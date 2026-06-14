"""app.py — SnapQuest backend.

Architecture:
  - Gradio exposes named API endpoints only (no UI components)
  - index.html serves the full game UI as a static file
  - JS in index.html calls /run/upload, /run/action etc. directly
  - Zero gr.HTML, zero SSE timing issues, zero iframe sandbox problems
"""
import base64
import json
import os
import tempfile

import gradio as gr

from engine_photo import start_photo_game, take_photo_action
from dungeon import current_room, can_advance
from game_data import roll_loot
from vision import analyze_scene
from voice import clean_for_speech, speak, transcribe_audio


# ── Session store (keyed by session_hash) ───────────────────────────────────
_SESSIONS: dict[str, dict] = {}

def _get(sid: str) -> dict:
    if sid not in _SESSIONS:
        _SESSIONS[sid] = {
            "photos": [],
            "selected_class": None,
            "game": {},
        }
    return _SESSIONS[sid]

def _save_b64(data_url: str) -> str:
    header, b64 = (data_url.split(",", 1) if "," in data_url else ("", data_url))
    ext = ".png" if "png" in header else ".webp" if "webp" in header else ".jpg"
    raw = base64.b64decode(b64)
    fd, path = tempfile.mkstemp(prefix="sq_", suffix=ext, dir="/tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return path

def _fmt_story(state: dict) -> str:
    if not state.get("rooms"):
        return "The dungeon awaits..."
    room = current_room(state)
    diff = room.get("difficulty", "").upper()
    sym  = {"EASY": "◆", "MEDIUM": "◈", "HARD": "⬡"}.get(diff, "◆")
    lines = [
        f"{'─'*5} {sym} {room.get('scene_name','Unknown')} {sym} {'─'*5}",
        "",
        room.get("scene_description", ""),
    ]
    for entry in state.get("history", [])[-8:]:
        lines.append(f"\n▷ {entry.get('action','')}")
        st = entry.get("response", {}).get("story", "")
        if st:
            lines.append(st)
    if can_advance(state):
        lines.append("\n\n[ Room cleared — click DESCEND DEEPER ]")
    return "\n".join(str(l) for l in lines if l is not None)


# ── API endpoints ─────────────────────────────────────────────────────────────

def api_upload(sid: str, slot: int, data_url: str, name: str) -> str:
    app = _get(sid)
    photos = list(app.get("photos", []))
    while len(photos) <= slot:
        photos.append({})
    if not data_url:
        photos[slot] = {}
        app["photos"] = photos
        return json.dumps({"ok": True, "photos": _photos_summary(photos)})
    try:
        path = _save_b64(data_url)
        scene = analyze_scene(path, "Rogue")
        objects = scene.get("objects_found", [])
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    photos[slot] = {"path": path, "objects": objects, "name": name}
    app["photos"] = photos
    return json.dumps({"ok": True, "photos": _photos_summary(photos)})

def _photos_summary(photos):
    return [
        {"has": bool(p.get("path")), "objects": p.get("objects", []), "name": p.get("name", "")}
        for p in photos
    ]

def api_start(sid: str, character_class: str) -> str:
    app = _get(sid)
    photos = app.get("photos", [])
    paths  = [p["path"] for p in photos if p.get("path")]
    if not paths:
        return json.dumps({"ok": False, "error": "No photos uploaded"})
    try:
        gs = start_photo_game(paths, character_class)
        app["game"] = gs
        app["selected_class"] = character_class
        return json.dumps({"ok": True, "state": _serialize_state(gs)})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})

def api_action(sid: str, text: str) -> str:
    app = _get(sid)
    gs  = app.get("game", {})
    if not gs.get("rooms"):
        return json.dumps({"ok": False, "error": "No active game"})
    if not text.strip():
        return json.dumps({"ok": True, "state": _serialize_state(gs), "loot": []})
    try:
        was_cleared = current_room(gs).get("cleared", False)
        new_gs, parsed = take_photo_action(gs, text)
        loot = []
        room_after = current_room(new_gs)
        if room_after.get("cleared") and not was_cleared:
            n = 3 if room_after.get("is_boss") else 2
            loot = roll_loot(n)
            new_gs["inventory"] = new_gs.get("inventory", []) + loot
        app["game"] = new_gs
        audio_b64 = ""
        try:
            txt = clean_for_speech(parsed)
            if txt:
                path = speak(txt)
                with open(path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()
        except Exception:
            pass
        return json.dumps({
            "ok": True,
            "state": _serialize_state(new_gs),
            "loot": loot,
            "audio_b64": audio_b64,
            "story": parsed.get("story", ""),
        })
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})

def api_voice(sid: str, audio_b64: str) -> str:
    if not audio_b64:
        return json.dumps({"ok": False, "text": ""})
    try:
        raw = base64.b64decode(audio_b64)
        fd, path = tempfile.mkstemp(suffix=".wav", dir="/tmp")
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        text = transcribe_audio(path)
        if not text:
            return json.dumps({"ok": False, "text": ""})
        result = json.loads(api_action(sid, text))
        result["transcribed"] = text
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc), "text": ""})

def api_state(sid: str) -> str:
    app = _get(sid)
    gs  = app.get("game", {})
    return json.dumps({
        "ok": True,
        "photos": _photos_summary(app.get("photos", [])),
        "selected_class": app.get("selected_class"),
        "has_game": bool(gs.get("rooms")),
        "state": _serialize_state(gs) if gs.get("rooms") else {},
    })

def _serialize_state(gs: dict) -> dict:
    rooms = gs.get("rooms", [])
    idx   = gs.get("room_index", 0)
    room  = rooms[min(idx, len(rooms)-1)] if rooms else {}
    boss  = room.get("boss") if room.get("is_boss") else None
    return {
        "hp": gs.get("hp", 100),
        "max_hp": gs.get("max_hp", 100),
        "xp": gs.get("xp", 0),
        "level": 1 + gs.get("xp", 0) // 100,
        "inventory": gs.get("inventory", []),
        "character_class": gs.get("character_class", ""),
        "room_index": idx,
        "total_rooms": len(rooms),
        "room": {
            "scene_name": room.get("scene_name", ""),
            "scene_description": room.get("scene_description", ""),
            "atmosphere": room.get("atmosphere", ""),
            "objects_found": room.get("objects_found", []),
            "difficulty": room.get("difficulty", "easy"),
            "is_boss": room.get("is_boss", False),
            "cleared": room.get("cleared", False),
            "enemy_alive": room.get("enemy_alive", True),
            "enemy_hp": room.get("enemy_hp", 30),
            "enemy_max_hp": room.get("enemy_max_hp", 30),
        },
        "boss": {
            "name": boss.get("name", "") if boss else "",
            "hp": boss.get("hp", 0) if boss else 0,
            "max_hp": boss.get("max_hp", 100) if boss else 100,
            "alive": boss.get("alive", True) if boss else False,
        } if boss else None,
        "choices": gs.get("current_choices", ["Look around", "Move forward", "Hold position"]),
        "story": _fmt_story(gs),
        "rooms_summary": [
            {"cleared": r.get("cleared", False), "is_boss": r.get("is_boss", False), "scene_name": r.get("scene_name","")}
            for r in rooms
        ],
    }


# ── Gradio app — API only, no visible UI ────────────────────────────────────

with gr.Blocks(title="SnapQuest API") as demo:
    gr.Markdown("## SnapQuest API — open the App tab to play")

    with gr.Row():
        sid_box    = gr.Textbox(label="sid",   visible=False)
        result_box = gr.Textbox(label="result", visible=False)

    # Upload endpoint
    with gr.Row(visible=False):
        up_sid  = gr.Textbox(); up_slot = gr.Number(); up_data = gr.Textbox(); up_name = gr.Textbox()
        up_out  = gr.Textbox()
        up_btn  = gr.Button("upload", elem_id="sq-api-upload")
    up_btn.click(api_upload, inputs=[up_sid, up_slot, up_data, up_name], outputs=[up_out], api_name="upload")

    # Start endpoint
    with gr.Row(visible=False):
        st_sid = gr.Textbox(); st_cls = gr.Textbox()
        st_out = gr.Textbox()
        st_btn = gr.Button("start", elem_id="sq-api-start")
    st_btn.click(api_start, inputs=[st_sid, st_cls], outputs=[st_out], api_name="start")

    # Action endpoint
    with gr.Row(visible=False):
        ac_sid = gr.Textbox(); ac_txt = gr.Textbox()
        ac_out = gr.Textbox()
        ac_btn = gr.Button("action", elem_id="sq-api-action")
    ac_btn.click(api_action, inputs=[ac_sid, ac_txt], outputs=[ac_out], api_name="action")

    # State endpoint
    with gr.Row(visible=False):
        gs_sid = gr.Textbox()
        gs_out = gr.Textbox()
        gs_btn = gr.Button("getstate", elem_id="sq-api-state")
    gs_btn.click(api_state, inputs=[gs_sid], outputs=[gs_out], api_name="getstate")

    # Voice endpoint
    with gr.Row(visible=False):
        vo_sid = gr.Textbox(); vo_data = gr.Textbox()
        vo_out = gr.Textbox()
        vo_btn = gr.Button("voice", elem_id="sq-api-voice")
    vo_btn.click(api_voice, inputs=[vo_sid, vo_data], outputs=[vo_out], api_name="voice")


demo.queue().launch(
    show_api=True,
    ssr_mode=False,
    allowed_paths=["/tmp", tempfile.gettempdir()],
)