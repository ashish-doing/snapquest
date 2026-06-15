"""app.py — SnapQuest.

ARCHITECTURE (the fix):
  - We create OUR OWN FastAPI app. It owns "/" and serves index.html.
  - Gradio is mounted as a SUB-APPLICATION at "/gradio" via gr.mount_gradio_app().
  - Gradio's own API endpoints therefore live at:
        /gradio/gradio_api/run/upload
        /gradio/gradio_api/run/start
        /gradio/gradio_api/run/action
        /gradio/gradio_api/run/voice
  - index.html calls these via a RELATIVE path: `/gradio/gradio_api/run/<endpoint>`
    (relative — works on the HF Space URL, localhost, or any deployment domain).

This is the ONLY architecture that survives `launch()` / Spaces SDK boot,
because we never ask Gradio to be the root ASGI app — so it can never
override our "/" route. uvicorn serves OUR app; gradio is just a mounted
child.
"""
import base64
import json
import os
import tempfile

import gradio as gr
from fastapi import FastAPI
from fastapi.responses import FileResponse

from engine_photo import start_photo_game, take_photo_action
from dungeon import current_room, can_advance
from game_data import roll_loot
from vision import analyze_scene
from voice import clean_for_speech, speak, transcribe_audio

_HERE = os.path.dirname(os.path.abspath(__file__))

# ── Session store ─────────────────────────────────────────────────────────────
_SESSIONS: dict = {}

def _get(sid: str) -> dict:
    if sid not in _SESSIONS:
        _SESSIONS[sid] = {"photos": [], "selected_class": None, "game": {}}
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
    lines = [f"{'─'*5} {sym} {room.get('scene_name','Unknown')} {sym} {'─'*5}", "",
             room.get("scene_description", "")]
    for entry in state.get("history", [])[-8:]:
        lines.append(f"\n▷ {entry.get('action','')}")
        st = entry.get("response", {}).get("story", "")
        if st: lines.append(st)
    if can_advance(state):
        lines.append("\n\n[ Room cleared — click DESCEND DEEPER ]")
    return "\n".join(str(l) for l in lines if l is not None)

def _photos_summary(photos):
    return [{"has": bool(p.get("path")), "objects": p.get("objects", []), "name": p.get("name", "")}
            for p in photos]

def _serialize_state(gs: dict) -> dict:
    rooms = gs.get("rooms", [])
    idx   = gs.get("room_index", 0)
    room  = rooms[min(idx, len(rooms)-1)] if rooms else {}
    boss  = room.get("boss") if room.get("is_boss") else None
    return {
        "hp": gs.get("hp", 100), "max_hp": gs.get("max_hp", 100),
        "xp": gs.get("xp", 0),   "level": 1 + gs.get("xp", 0) // 100,
        "inventory": gs.get("inventory", []),
        "character_class": gs.get("character_class", ""),
        "room_index": idx, "total_rooms": len(rooms),
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
        "boss": {"name": boss.get("name",""), "hp": boss.get("hp",0),
                 "max_hp": boss.get("max_hp",100), "alive": boss.get("alive",True)
                 } if boss else None,
        "choices": gs.get("current_choices", ["Look around","Move forward","Hold position"]),
        "story": _fmt_story(gs),
        "rooms_summary": [{"cleared": r.get("cleared",False), "is_boss": r.get("is_boss",False),
                           "scene_name": r.get("scene_name","")} for r in rooms],
    }

# ── Gradio API functions ──────────────────────────────────────────────────────

def api_upload(sid: str, slot: float, data_url: str, name: str) -> str:
    app = _get(sid)
    slot = int(slot)
    photos = list(app.get("photos", []))
    while len(photos) <= slot: photos.append({})
    if not data_url:
        photos[slot] = {}; app["photos"] = photos
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

def api_start(sid: str, character_class: str) -> str:
    app = _get(sid)
    paths = [p["path"] for p in app.get("photos", []) if p.get("path")]
    if not paths:
        return json.dumps({"ok": False, "error": "No photos uploaded"})
    try:
        gs = start_photo_game(paths, character_class)
        app["game"] = gs; app["selected_class"] = character_class
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
                apath = speak(txt)
                with open(apath, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode()
        except Exception:
            pass
        return json.dumps({"ok": True, "state": _serialize_state(new_gs),
                           "loot": loot, "audio_b64": audio_b64,
                           "story": parsed.get("story", "")})
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc)})

def api_voice(sid: str, audio_b64: str) -> str:
    if not audio_b64:
        return json.dumps({"ok": False, "text": ""})
    try:
        raw = base64.b64decode(audio_b64)
        fd, path = tempfile.mkstemp(suffix=".wav", dir="/tmp")
        with os.fdopen(fd, "wb") as f: f.write(raw)
        text = transcribe_audio(path)
        if not text:
            return json.dumps({"ok": False, "text": ""})
        result = json.loads(api_action(sid, text))
        result["transcribed"] = text
        return json.dumps(result)
    except Exception as exc:
        return json.dumps({"ok": False, "error": str(exc), "text": ""})

# ── Gradio Blocks (API-only, hidden) ───────────────────────────────────────────

with gr.Blocks(title="SnapQuest API") as gradio_app:
    gr.Markdown("### SnapQuest API backend\n\nThis surface only exposes API endpoints "
                 "consumed by the game UI at the [root URL](/). "
                 "Visit `/` for the actual game.")
    with gr.Row(visible=False):
        gr.Button().click(api_upload,
            inputs=[gr.Textbox(), gr.Number(), gr.Textbox(), gr.Textbox()],
            outputs=[gr.Textbox()], api_name="upload")
    with gr.Row(visible=False):
        gr.Button().click(api_start,
            inputs=[gr.Textbox(), gr.Textbox()],
            outputs=[gr.Textbox()], api_name="start")
    with gr.Row(visible=False):
        gr.Button().click(api_action,
            inputs=[gr.Textbox(), gr.Textbox()],
            outputs=[gr.Textbox()], api_name="action")
    with gr.Row(visible=False):
        gr.Button().click(api_voice,
            inputs=[gr.Textbox(), gr.Textbox()],
            outputs=[gr.Textbox()], api_name="voice")

# ── FastAPI app (THIS is root — owns "/") ──────────────────────────────────────

fastapi_app = FastAPI(title="SnapQuest")

@fastapi_app.get("/")
async def serve_index():
    return FileResponse(os.path.join(_HERE, "index.html"))

@fastapi_app.get("/game")
async def serve_game():
    # Alias kept for backwards-compat with anything linking to /game
    return FileResponse(os.path.join(_HERE, "index.html"))

@fastapi_app.get("/health")
async def health():
    return {"status": "ok"}

# Mount Gradio as a SUB-app at /gradio. Its API lives at
# /gradio/gradio_api/run/<endpoint>  — Gradio never touches "/".
fastapi_app = gr.mount_gradio_app(fastapi_app, gradio_app, path="/gradio")

# Expose `app` for `python app.py` / uvicorn / HF Spaces SDK detection.
app = fastapi_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))