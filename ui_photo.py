"""ui_photo.py — SnapQuest v7
Root cause fix: gr.HTML inside gr.Blocks on HF Spaces 5.9.1 only renders reliably
when it is the OUTPUT of an event. demo.load() fires over SSE which HF's iframe
sandbox drops before the component hydrates.

Solution: use gr.HTML as a purely output-driven component with NO initial value,
and trigger render via a tiny <script> injected into a gr.HTML("") that auto-clicks
the hidden button 300ms after page load — before any SSE is needed, using only
the DOM that's already painted.
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


# ── State ────────────────────────────────────────────────────────────────────

def _new_state() -> dict:
    return {"screen": "s1", "photos": [], "selected_class": None, "game": {}}


# ── Story formatter ──────────────────────────────────────────────────────────

def _format_story(state: dict) -> str:
    if not state.get("rooms"):
        return "The dungeon awaits..."
    room = current_room(state)
    diff = room.get("difficulty", "").upper()
    sym  = {"EASY": "◆", "MEDIUM": "◈", "HARD": "⬡"}.get(diff, "◆")
    lines = [
        "{sep} {sym} {name} {sym} {sep}".format(sep="─"*5, sym=sym, name=room.get("scene_name","Unknown")),
        "",
        room.get("scene_description", ""),
    ]
    for entry in state.get("history", [])[-8:]:
        act  = entry.get("action", "")
        resp = entry.get("response", {})
        st   = resp.get("story", "")
        lines.append(f"\n▷ {act}")
        if st:
            lines.append(st)
    if can_advance(state):
        lines.append("\n\n[ Room cleared — click DESCEND DEEPER to advance ]")
    return "\n".join(str(l) for l in lines if l is not None)


# ── Base64 decode ─────────────────────────────────────────────────────────────

def _save_b64(data_url: str) -> str:
    if "," in data_url:
        header, b64 = data_url.split(",", 1)
    else:
        header, b64 = "", data_url
    ext = ".png" if "png" in header else ".webp" if "webp" in header else ".jpg"
    raw = base64.b64decode(b64)
    fd, path = tempfile.mkstemp(prefix="sq_", suffix=ext, dir="/tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return path


# ── Handlers ──────────────────────────────────────────────────────────────────

def _handle_upload(app, cmd):
    slot = int(cmd.get("slot", 0))
    data_url = cmd.get("data", "")
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
    try:
        scene   = analyze_scene(path, "Rogue")
        objects = scene.get("objects_found", [])
    except Exception:
        objects = ["mysterious object"]
    photos[slot] = {"path": path, "objects": objects, "name": cmd.get("name","photo")}
    app["photos"] = photos
    return app, screen1_html(photos)


def _handle_goto_class(app, cmd):
    app["screen"] = "s2"
    n = sum(1 for p in app.get("photos",[]) if p.get("path"))
    summary = {1:"1 photo → 1-room dungeon (straight to boss)",
               2:"2 photos → 2-room dungeon (entry + boss)",
               3:"3 photos → 3-room dungeon (entry, chamber, boss)"}.get(n,"")
    return app, screen2_html(app.get("selected_class"), summary)


def _handle_select_class(app, cmd):
    cls = cmd.get("cls","Swordsman")
    app["selected_class"] = cls
    n = sum(1 for p in app.get("photos",[]) if p.get("path"))
    summary = {1:"1 photo → 1-room dungeon (straight to boss)",
               2:"2 photos → 2-room dungeon (entry + boss)",
               3:"3 photos → 3-room dungeon (entry, chamber, boss)"}.get(n,"")
    return app, screen2_html(cls, summary)


def _handle_start_dungeon(app, cmd):
    photos = app.get("photos",[])
    paths  = [p["path"] for p in photos if p.get("path")]
    cls    = app.get("selected_class") or "Swordsman"
    if not paths:
        app["screen"] = "s1"
        return app, screen1_html(photos)
    try:
        gs = start_photo_game(paths, cls)
        app["game"]   = gs
        app["screen"] = "s3"
        return app, screen3_html(gs, _format_story(gs), None)
    except Exception as exc:
        return app, error_html(f"Could not build dungeon: {exc}")


def _handle_action(app, cmd):
    text = cmd.get("text","").strip()
    gs   = app.get("game",{})
    if not gs.get("rooms"):
        return app, screen1_html(app.get("photos",[])), None
    if not text:
        return app, screen3_html(gs, _format_story(gs), None), None
    try:
        was_cleared = current_room(gs).get("cleared", False)
        new_gs, parsed = take_photo_action(gs, text)
        loot = None
        room_after = current_room(new_gs)
        if room_after.get("cleared") and not was_cleared:
            n = 3 if room_after.get("is_boss") else 2
            loot = roll_loot(n)
            new_gs["inventory"] = new_gs.get("inventory",[]) + loot
        app["game"] = new_gs
        story = _format_story(new_gs)
        audio_path = None
        try:
            txt = clean_for_speech(parsed)
            if txt:
                audio_path = speak(txt)
        except Exception:
            pass
        return app, screen3_html(new_gs, story, loot), audio_path
    except Exception as exc:
        story = _format_story(gs) + f"\n\n[error] {exc}"
        return app, screen3_html(gs, story, None), None


def _handle_go_back(app, cmd):
    target = cmd.get("to","s1")
    app["screen"] = target
    if target == "s1":
        return app, screen1_html(app.get("photos",[]))
    if target == "s2":
        return app, screen2_html(app.get("selected_class"))
    if target == "s3" and app.get("game",{}).get("rooms"):
        gs = app["game"]
        return app, screen3_html(gs, _format_story(gs), None)
    return app, screen1_html(app.get("photos",[]))


def _render_current(app):
    s = app.get("screen","s1")
    if s == "s1": return screen1_html(app.get("photos",[]))
    if s == "s2": return screen2_html(app.get("selected_class"))
    if s == "s3" and app.get("game",{}).get("rooms"):
        gs = app["game"]; return screen3_html(gs, _format_story(gs), None)
    return screen1_html(app.get("photos",[]))


# ── Main dispatch ─────────────────────────────────────────────────────────────

def _dispatch(cmd_json: str, app: dict):
    app = app or _new_state()
    if not cmd_json or not cmd_json.strip():
        # This is the INIT call — return screen1
        return app, screen1_html(app.get("photos",[])), None
    try:
        cmd = json.loads(cmd_json)
    except Exception:
        return app, _render_current(app), None
    action = cmd.get("cmd","")
    if   action == "upload":        new_app, html = _handle_upload(app, cmd);        return new_app, html, None
    elif action == "goto_class":    new_app, html = _handle_goto_class(app, cmd);    return new_app, html, None
    elif action == "select_class":  new_app, html = _handle_select_class(app, cmd);  return new_app, html, None
    elif action == "start_dungeon": new_app, html = _handle_start_dungeon(app, cmd); return new_app, html, None
    elif action == "action":        return _handle_action(app, cmd)
    elif action == "go_back":       new_app, html = _handle_go_back(app, cmd);       return new_app, html, None
    return app, _render_current(app), None


def _on_voice(audio_path, app):
    app = app or _new_state()
    if not audio_path:
        return app, _render_current(app), None, ""
    try:
        text = transcribe_audio(audio_path)
    except Exception:
        text = ""
    if not text:
        return app, _render_current(app), None, ""
    new_app, html, audio = _handle_action(app, {"cmd":"action","text":text})
    return new_app, html, audio, text


# ── CSS ───────────────────────────────────────────────────────────────────────

_CSS = """
.gradio-container {
    background: #08090d !important;
    margin: 0 !important; padding: 0 !important;
    max-width: 100% !important;
}
footer { display: none !important; }
#sq-bridge-row { display: none !important; }
#sq-init-row   { display: none !important; }
#sq-voice-row  {
    background: #0d0e14 !important;
    border-top: 1px solid #2a2418 !important;
    padding: 8px 16px !important;
}
/* Make the HTML panel fill its container */
#sq-main { min-height: 85vh !important; }
#sq-main > div,
#sq-main .html-container { min-height: 85vh !important; }
"""

# ── AUTOCLICK TRIGGER ─────────────────────────────────────────────────────────
# This small HTML block is painted synchronously by Gradio's SSR pass.
# It uses setTimeout(0) so it runs after the Svelte components mount,
# then clicks the hidden init button — no WebSocket/SSE needed for this step.
_AUTOCLICK_HTML = """
<div id="sq-autoclick" style="display:none"></div>
<script>
(function poll() {
  var btn = document.querySelector('#sq-init-btn button');
  if (btn) { btn.click(); return; }
  setTimeout(poll, 80);
})();
</script>
"""


# ── Gradio layout ─────────────────────────────────────────────────────────────

with gr.Blocks(css=_CSS, title="SNAPQUEST ⚔") as demo:
    app_state = gr.State(_new_state())

    # Autoclick trigger — rendered synchronously by Gradio SSR
    gr.HTML(_AUTOCLICK_HTML)

    # Game canvas — starts empty, filled by init button click
    main_html = gr.HTML(value="", elem_id="sq-main")

    # Hidden init button — clicked by the autoclick script above
    with gr.Row(elem_id="sq-init-row", visible=False):
        init_btn = gr.Button("init", elem_id="sq-init-btn")

    # Hidden command bridge
    with gr.Row(elem_id="sq-bridge-row", visible=False):
        cmd_box = gr.Textbox(label="cmd", elem_id="sq-cmd-box")
        cmd_btn = gr.Button("send", elem_id="sq-cmd-btn")

    # Voice row
    with gr.Row(elem_id="sq-voice-row"):
        voice_in    = gr.Audio(sources=["microphone"], type="filepath",
                               label="🎙 Voice Action")
        voice_out   = gr.Audio(label="⚔ DM Voice", autoplay=True)
        transcribed = gr.Textbox(label="Transcribed", scale=2)

    # Init click → render screen1 (empty cmd_json → returns screen1)
    init_btn.click(
        _dispatch,
        inputs=[gr.Textbox(value="", visible=False), app_state],
        outputs=[app_state, main_html, voice_out],
        api_name=False,
    )

    # Command bridge
    cmd_btn.click(
        _dispatch,
        inputs=[cmd_box, app_state],
        outputs=[app_state, main_html, voice_out],
        api_name=False,
    )

    # Voice
    voice_in.stop_recording(
        _on_voice,
        inputs=[voice_in, app_state],
        outputs=[app_state, main_html, voice_out, transcribed],
        api_name=False,
    )