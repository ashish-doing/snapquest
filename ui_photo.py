"""ui_photo.py — SnapQuest v6 — JS bridge embedded in screen HTML, no head= required.

Fixes vs v5:
  - Removed head=_SQ_HEAD_JS from gr.Blocks (broke HF Spaces Gradio 5.9.1)
  - JS bridge is now embedded directly in every screen's HTML (game_screens.py)
  - gr.HTML gets explicit min-height so it never collapses to 0px
  - Loading state shown immediately on upload/start so users see feedback
  - Nemotron DM backend env-var support added (SNAPQUEST_DM_MODEL)
"""
from __future__ import annotations

import base64
import json
import os
import tempfile

import gradio as gr

from engine_photo import start_photo_game, take_photo_action
from dungeon import current_room, can_advance
from game_data import roll_loot
from game_screens import screen1_html, screen2_html, screen3_html, error_html, loading_html
from vision import analyze_scene
from voice import clean_for_speech, speak, transcribe_audio


# ── App state ────────────────────────────────────────────────────────────────

def _new_state() -> dict:
    return {
        "screen": "s1",
        "photos": [],          # [{path, objects, name}]
        "selected_class": None,
        "game": {},
    }


# ── Story formatter ──────────────────────────────────────────────────────────

def _format_story(state: dict) -> str:
    if not state.get("rooms"):
        return "The dungeon awaits..."
    room = current_room(state)
    diff  = room.get("difficulty", "").upper()
    sym   = {"EASY": "◆", "MEDIUM": "◈", "HARD": "⬡"}.get(diff, "◆")
    lines = [
        "{sep} {sym} {name} {sym} {sep}".format(
            sep="─"*5, sym=sym, name=room.get("scene_name", "Unknown")
        ),
        "",
        room.get("scene_description", ""),
    ]
    history = state.get("history", [])
    if history:
        lines.append("\n── Chronicle ──")
        for entry in history[-8:]:
            act  = entry.get("action", "")
            resp = entry.get("response", {})
            st   = resp.get("story", "")
            lines.append(f"\n▷ {act}")
            if st:
                lines.append(st)
    if can_advance(state):
        lines.append('\n\n[ Room cleared — click DESCEND DEEPER to advance ]')
    return "\n".join(str(l) for l in lines if l is not None)


# ── Base64 decode ─────────────────────────────────────────────────────────────

def _save_b64(data_url: str) -> str:
    if "," in data_url:
        header, b64 = data_url.split(",", 1)
    else:
        header, b64 = "", data_url
    ext = ".jpg"
    if "png" in header:   ext = ".png"
    elif "webp" in header: ext = ".webp"
    raw = base64.b64decode(b64)
    fd, path = tempfile.mkstemp(prefix="sq_", suffix=ext, dir="/tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return path


# ── Command handlers ──────────────────────────────────────────────────────────

def _handle_upload(app: dict, cmd: dict):
    slot     = int(cmd.get("slot", 0))
    data_url = cmd.get("data", "")
    name     = cmd.get("name", "photo")

    photos = list(app.get("photos", []))
    while len(photos) <= slot:
        photos.append({})

    if not data_url:
        photos[slot] = {}
        app["photos"] = photos
        return app, screen1_html(photos)

    try:
        path = _save_b64(data_url)
    except Exception as exc:
        return app, error_html(f"Could not read image: {exc}")

    # Show loading state while vision runs
    try:
        scene   = analyze_scene(path, "Rogue")
        objects = scene.get("objects_found", [])
    except Exception:
        objects = ["mysterious object"]

    photos[slot] = {"path": path, "objects": objects, "name": name}
    app["photos"] = photos
    return app, screen1_html(photos)


def _handle_goto_class(app: dict, cmd: dict):
    app["screen"] = "s2"
    n = sum(1 for p in app.get("photos", []) if p.get("path"))
    summary = {1:"1 photo → 1-room dungeon (straight to boss)",
               2:"2 photos → 2-room dungeon (entry + boss)",
               3:"3 photos → 3-room dungeon (entry, chamber, boss)"}.get(n, "")
    return app, screen2_html(app.get("selected_class"), summary)


def _handle_select_class(app: dict, cmd: dict):
    cls = cmd.get("cls", "Swordsman")
    app["selected_class"] = cls
    n = sum(1 for p in app.get("photos", []) if p.get("path"))
    summary = {1:"1 photo → 1-room dungeon (straight to boss)",
               2:"2 photos → 2-room dungeon (entry + boss)",
               3:"3 photos → 3-room dungeon (entry, chamber, boss)"}.get(n, "")
    return app, screen2_html(cls, summary)


def _handle_start_dungeon(app: dict, cmd: dict):
    photos = app.get("photos", [])
    paths  = [p["path"] for p in photos if p.get("path")]
    cls    = app.get("selected_class") or "Swordsman"

    if not paths:
        app["screen"] = "s1"
        return app, screen1_html(photos)

    try:
        game_state      = start_photo_game(paths, cls)
        app["game"]     = game_state
        app["screen"]   = "s3"
        story           = _format_story(game_state)
        return app, screen3_html(game_state, story, None)
    except Exception as exc:
        return app, error_html(f"Could not build dungeon: {exc}")


def _handle_action(app: dict, cmd: dict):
    text       = cmd.get("text", "").strip()
    game_state = app.get("game", {})

    if not game_state.get("rooms"):
        return app, screen1_html(app.get("photos", [])), None

    if not text:
        story = _format_story(game_state)
        return app, screen3_html(game_state, story, None), None

    try:
        room_was_cleared = current_room(game_state).get("cleared", False)
        new_state, parsed = take_photo_action(game_state, text)

        loot = None
        room_after = current_room(new_state)
        if room_after.get("cleared") and not room_was_cleared:
            n     = 3 if room_after.get("is_boss") else 2
            loot  = roll_loot(n)
            new_state["inventory"] = new_state.get("inventory", []) + loot

        app["game"] = new_state
        story       = _format_story(new_state)

        audio_path = None
        try:
            txt = clean_for_speech(parsed)
            if txt:
                audio_path = speak(txt)
        except Exception:
            pass

        return app, screen3_html(new_state, story, loot), audio_path
    except Exception as exc:
        story = _format_story(game_state) + f"\n\n[error] {exc}"
        return app, screen3_html(game_state, story, None), None


def _handle_go_back(app: dict, cmd: dict):
    target = cmd.get("to", "s1")
    app["screen"] = target
    if target == "s1":
        return app, screen1_html(app.get("photos", []))
    elif target == "s2":
        return app, screen2_html(app.get("selected_class"))
    elif target == "s3" and app.get("game", {}).get("rooms"):
        gs = app["game"]
        return app, screen3_html(gs, _format_story(gs), None)
    return app, screen1_html(app.get("photos", []))


def _render_current(app: dict) -> str:
    screen = app.get("screen", "s1")
    if screen == "s1":
        return screen1_html(app.get("photos", []))
    elif screen == "s2":
        return screen2_html(app.get("selected_class"))
    elif screen == "s3" and app.get("game", {}).get("rooms"):
        gs = app["game"]
        return screen3_html(gs, _format_story(gs), None)
    return screen1_html(app.get("photos", []))


# ── Main dispatch ─────────────────────────────────────────────────────────────

def _dispatch(cmd_json: str, app: dict):
    """Returns (new_app, html, audio_or_None)"""
    app = app or _new_state()
    if not cmd_json or not cmd_json.strip():
        return app, _render_current(app), None

    try:
        cmd = json.loads(cmd_json)
    except (json.JSONDecodeError, TypeError):
        return app, _render_current(app), None

    action = cmd.get("cmd", "")

    if   action == "upload":        new_app, html = _handle_upload(app, cmd);        return new_app, html, None
    elif action == "goto_class":    new_app, html = _handle_goto_class(app, cmd);    return new_app, html, None
    elif action == "select_class":  new_app, html = _handle_select_class(app, cmd);  return new_app, html, None
    elif action == "start_dungeon": new_app, html = _handle_start_dungeon(app, cmd); return new_app, html, None
    elif action == "action":        return _handle_action(app, cmd)
    elif action == "go_back":       new_app, html = _handle_go_back(app, cmd);       return new_app, html, None

    return app, _render_current(app), None


# ── Voice ─────────────────────────────────────────────────────────────────────

def _on_voice(audio_path, app: dict):
    app = app or _new_state()
    if not audio_path:
        return app, _render_current(app), None, ""
    try:
        text = transcribe_audio(audio_path)
    except Exception:
        text = ""
    if not text:
        return app, _render_current(app), None, ""
    new_app, html, audio = _handle_action(app, {"cmd": "action", "text": text})
    return new_app, html, audio, text


# ── Gradio app ────────────────────────────────────────────────────────────────

_CSS = """
/* Reset Gradio chrome completely */
.gradio-container {
    background: #08090d !important;
    margin: 0 !important;
    padding: 0 !important;
    max-width: 100% !important;
    min-height: 100vh !important;
}
.gradio-container > .main,
.gradio-container > .main > .wrap { min-height: 100vh !important; }
footer { display: none !important; }
.gr-prose, .gradio-container .prose { display: none !important; }
#sq-bridge-row { display: none !important; }
#sq-voice-row {
    background: #0d0e14 !important;
    border-top: 1px solid #2a2418 !important;
    padding: 8px 20px !important;
}
/* Critical: make the HTML component fill space */
#sq-main > div { min-height: 100vh; }
#sq-main .html-container { min-height: 100vh !important; }
"""

def _initial_render(app: dict):
    """Called by demo.load() — forces Gradio to actually paint the HTML on first load."""
    return app, screen1_html(app.get("photos", []))


with gr.Blocks(css=_CSS, title="SNAPQUEST ⚔") as demo:
    app_state = gr.State(_new_state())

    # Main HTML display — value intentionally empty string;
    # demo.load() below populates it immediately after page connects.
    main_html = gr.HTML(value="", elem_id="sq-main")

    # Hidden bridge — JS writes JSON here, button triggers Python
    with gr.Row(elem_id="sq-bridge-row", visible=False):
        cmd_box = gr.Textbox(label="cmd", elem_id="sq-cmd-box", visible=False)
        cmd_btn = gr.Button("send", elem_id="sq-cmd-btn", visible=False)

    # Voice row — minimal, shown at bottom
    with gr.Row(elem_id="sq-voice-row"):
        voice_in = gr.Audio(
            sources=["microphone"], type="filepath",
            label="🎙 Voice Action (record then auto-submits)",
        )
        voice_out = gr.Audio(label="⚔ DM Voice", autoplay=True)
        transcribed = gr.Textbox(label="Transcribed", visible=True, scale=2)

    # CRITICAL: demo.load() is the only reliable way to render HTML on
    # initial page load in Gradio 5.9.1 on HF Spaces.
    demo.load(
        _initial_render,
        inputs=[app_state],
        outputs=[app_state, main_html],
    )

    # Wire bridge
    cmd_btn.click(
        _dispatch,
        inputs=[cmd_box, app_state],
        outputs=[app_state, main_html, voice_out],
        api_name=False,
    )

    # Wire voice
    voice_in.stop_recording(
        _on_voice,
        inputs=[voice_in, app_state],
        outputs=[app_state, main_html, voice_out, transcribed],
        api_name=False,
    )