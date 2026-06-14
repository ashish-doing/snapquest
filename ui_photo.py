"""ui_photo.py — SnapQuest v5 — Pure HTML/JS game UI with minimal Gradio bridge.

Architecture:
  - Single gr.HTML renders the entire game (3 screens)
  - Single hidden gr.Textbox + gr.Button carry JSON commands from JS to Python
  - All photo uploads go through base64 (FileReader in browser) — no gr.Image
  - voice.py is wired via small hidden gr.Audio components for STT/TTS
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
from game_screens import screen1_html, screen2_html, screen3_html, error_html
from vision import analyze_scene
from voice import clean_for_speech, speak, transcribe_audio



_SQ_HEAD_JS = """
<script>
window.__sq_initialized = false;

function __sq_init_bridge() {
  if (window.__sq_initialized) return;

  function findHidden() {
    var box = document.querySelector("#sq-cmd-box textarea");
    var btn = document.querySelector("#sq-cmd-btn button");
    return {box: box, btn: btn};
  }

  window.__sq_send = function(cmdObj) {
    var els = findHidden();
    if (!els.box || !els.btn) {
      setTimeout(function(){ window.__sq_send(cmdObj); }, 200);
      return;
    }
    var jsonStr = JSON.stringify(cmdObj);
    // Use native setter to bypass React-controlled value tracking
    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
    nativeSetter.call(els.box, jsonStr);
    els.box.dispatchEvent(new Event("input", {bubbles: true}));
    setTimeout(function() { els.btn.click(); }, 50);
  };

  window.__sq_action = function(text) {
    if (!text || !text.trim()) return;
    window.__sq_send({cmd: "action", text: text});
    var inp = document.getElementById("sq-custom-input");
    if (inp) inp.value = "";
  };

  window.__sq_goto_class = function() {
    window.__sq_send({cmd: "goto_class"});
  };

  window.__sq_select_class = function(cls) {
    window.__sq_send({cmd: "select_class", cls: cls});
  };

  window.__sq_start_dungeon = function() {
    window.__sq_send({cmd: "start_dungeon"});
  };

  window.__sq_go_back = function(screen) {
    window.__sq_send({cmd: "go_back", to: screen});
  };

  window.__sq_pick_file = function(slot) {
    var input = document.getElementById("sq-file-input-" + slot);
    if (input) input.click();
  };

  window.__sq_handle_file = function(slot, input) {
    if (!input.files || !input.files[0]) return;
    var file = input.files[0];
    var reader = new FileReader();
    reader.onload = function(e) {
      window.__sq_send({cmd: "upload", slot: slot, data: e.target.result, name: file.name});
    };
    reader.readAsDataURL(file);
  };

  window.__sq_initialized = true;
}

// Run on load and on every DOM mutation (Gradio re-renders the HTML component)
document.addEventListener("DOMContentLoaded", __sq_init_bridge);
__sq_init_bridge();
var __sq_observer = new MutationObserver(__sq_init_bridge);
__sq_observer.observe(document.body, {childList: true, subtree: true});
</script>
"""


# ── App state shape ──────────────────────────────────────────────────────────
def _new_app_state() -> dict:
    return {
        "screen": "s1",
        "photos": [],          # list of {path, objects, name}
        "selected_class": None,
        "game": {},             # populated by start_photo_game / take_photo_action
    }


# ── Story formatter ───────────────────────────────────────────────────────────
def _format_story(state: dict) -> str:
    if not state.get("rooms"):
        return "The dungeon awaits..."
    room = current_room(state)
    scene_name = room.get("scene_name", "Unknown")
    diff = room.get("difficulty", "").upper()
    sym = {"EASY": "◆", "MEDIUM": "◈", "HARD": "⬡"}.get(diff, "◆")
    lines = ["{0} {1} {2} {1} {0}".format("─" * 5, sym, scene_name), ""]
    lines.append(room.get("scene_description", ""))
    history = state.get("history", [])
    if history:
        lines.append("\n── Chronicle ──")
        for entry in history[-8:]:
            act = entry.get("action", "")
            resp = entry.get("response", {})
            st = resp.get("story", "")
            lines.append("\n▷ {}".format(act))
            if st:
                lines.append(st)
    if can_advance(state):
        lines.append('\n\n[ Room cleared — click "GO DEEPER" to advance! ]')
    return "\n".join(str(l) for l in lines if l is not None)


# ── Base64 image decode ──────────────────────────────────────────────────────
def _save_base64_image(data_url: str, name_hint: str = "photo") -> str:
    """Decode a data: URL and save to a temp file. Returns the file path."""
    if "," in data_url:
        header, b64data = data_url.split(",", 1)
    else:
        b64data = data_url
        header = ""

    ext = ".jpg"
    if "png" in header:
        ext = ".png"
    elif "webp" in header:
        ext = ".webp"
    elif "jpeg" in header or "jpg" in header:
        ext = ".jpg"

    raw = base64.b64decode(b64data)
    fd, path = tempfile.mkstemp(prefix="sq_", suffix=ext, dir="/tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(raw)
    return path


# ════════════════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ════════════════════════════════════════════════════════════════════════════

def _handle_upload(app_state: dict, cmd: dict) -> tuple[dict, str]:
    """Decode base64 photo, run vision analysis, update screen1."""
    slot = int(cmd.get("slot", 0))
    data_url = cmd.get("data", "")
    name = cmd.get("name", "photo")

    photos = list(app_state.get("photos", []))
    while len(photos) <= slot:
        photos.append({})

    if not data_url:
        photos[slot] = {}
        app_state["photos"] = photos
        return app_state, screen1_html(photos)

    try:
        path = _save_base64_image(data_url, name)
    except Exception as exc:
        photos[slot] = {}
        app_state["photos"] = photos
        return app_state, error_html("Could not read image: {}".format(exc))

    try:
        scene = analyze_scene(path, "Rogue")  # generic class for object detection preview
        objects = scene.get("objects_found", [])
    except Exception:
        objects = ["unknown object"]

    photos[slot] = {"path": path, "objects": objects, "name": name}
    app_state["photos"] = photos
    return app_state, screen1_html(photos)


def _handle_goto_class(app_state: dict, cmd: dict) -> tuple[dict, str]:
    app_state["screen"] = "s2"
    n_loaded = sum(1 for p in app_state.get("photos", []) if p.get("path"))
    summary = {
        1: "1 photo uploaded -> 1-room dungeon (boss room)",
        2: "2 photos uploaded -> 2-room dungeon (entry + boss)",
        3: "3 photos uploaded -> 3-room dungeon (entry, chamber, boss)",
    }.get(n_loaded, "")
    return app_state, screen2_html(app_state.get("selected_class"), summary)


def _handle_select_class(app_state: dict, cmd: dict) -> tuple[dict, str]:
    cls = cmd.get("cls", "Swordsman")
    app_state["selected_class"] = cls
    n_loaded = sum(1 for p in app_state.get("photos", []) if p.get("path"))
    summary = {
        1: "1 photo uploaded -> 1-room dungeon (boss room)",
        2: "2 photos uploaded -> 2-room dungeon (entry + boss)",
        3: "3 photos uploaded -> 3-room dungeon (entry, chamber, boss)",
    }.get(n_loaded, "")
    return app_state, screen2_html(cls, summary)


def _handle_start_dungeon(app_state: dict, cmd: dict) -> tuple[dict, str]:
    photos = app_state.get("photos", [])
    paths = [p["path"] for p in photos if p.get("path")]
    cls = app_state.get("selected_class") or "Swordsman"

    if not paths:
        app_state["screen"] = "s1"
        return app_state, screen1_html(photos)

    try:
        game_state = start_photo_game(paths, cls)
        app_state["game"] = game_state
        app_state["screen"] = "s3"
        story = _format_story(game_state)
        return app_state, screen3_html(game_state, story, None)
    except Exception as exc:
        return app_state, error_html("Could not build dungeon: {}".format(exc))


def _handle_action(app_state: dict, cmd: dict):
    """Returns (app_state, html, audio_path_or_none)"""
    text = cmd.get("text", "").strip()
    game_state = app_state.get("game", {})

    if not game_state.get("rooms"):
        return app_state, screen1_html(app_state.get("photos", [])), None

    if not text:
        story = _format_story(game_state)
        return app_state, screen3_html(game_state, story, None), None

    try:
        room_before_cleared = current_room(game_state).get("cleared", False)
        new_state, parsed = take_photo_action(game_state, text)

        loot = None
        room_after = current_room(new_state)
        if room_after.get("cleared") and not room_before_cleared:
            n = 3 if room_after.get("is_boss") else 2
            loot = roll_loot(n)
            new_state["inventory"] = new_state.get("inventory", []) + loot

        app_state["game"] = new_state
        story = _format_story(new_state)

        audio_path = None
        try:
            txt = clean_for_speech(parsed)
            if txt:
                audio_path = speak(txt)
        except Exception:
            pass

        return app_state, screen3_html(new_state, story, loot), audio_path

    except Exception as exc:
        story = _format_story(game_state) + "\n\n[error] {}".format(exc)
        return app_state, screen3_html(game_state, story, None), None


def _handle_go_back(app_state: dict, cmd: dict) -> tuple[dict, str]:
    target = cmd.get("to", "s1")
    app_state["screen"] = target
    if target == "s1":
        return app_state, screen1_html(app_state.get("photos", []))
    elif target == "s2":
        return app_state, screen2_html(app_state.get("selected_class"))
    elif target == "s3" and app_state.get("game", {}).get("rooms"):
        game_state = app_state["game"]
        return app_state, screen3_html(game_state, _format_story(game_state), None)
    return app_state, screen1_html(app_state.get("photos", []))


# ════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCH
# ════════════════════════════════════════════════════════════════════════════

def _dispatch(cmd_json: str, app_state: dict):
    """Returns (new_app_state, html_string, audio_path_or_None)"""
    app_state = app_state or _new_app_state()

    if not cmd_json or not cmd_json.strip():
        return app_state, _render_current(app_state), None

    try:
        cmd = json.loads(cmd_json)
    except (json.JSONDecodeError, TypeError):
        return app_state, _render_current(app_state), None

    action = cmd.get("cmd", "")

    if action == "upload":
        new_state, html = _handle_upload(app_state, cmd)
        return new_state, html, None

    elif action == "goto_class":
        new_state, html = _handle_goto_class(app_state, cmd)
        return new_state, html, None

    elif action == "select_class":
        new_state, html = _handle_select_class(app_state, cmd)
        return new_state, html, None

    elif action == "start_dungeon":
        new_state, html = _handle_start_dungeon(app_state, cmd)
        return new_state, html, None

    elif action == "action":
        new_state, html, audio = _handle_action(app_state, cmd)
        return new_state, html, audio

    elif action == "go_back":
        new_state, html = _handle_go_back(app_state, cmd)
        return new_state, html, None

    return app_state, _render_current(app_state), None


def _render_current(app_state: dict) -> str:
    screen = app_state.get("screen", "s1")
    if screen == "s1":
        return screen1_html(app_state.get("photos", []))
    elif screen == "s2":
        return screen2_html(app_state.get("selected_class"))
    elif screen == "s3" and app_state.get("game", {}).get("rooms"):
        game_state = app_state["game"]
        return screen3_html(game_state, _format_story(game_state), None)
    return screen1_html(app_state.get("photos", []))


# ════════════════════════════════════════════════════════════════════════════
# VOICE HANDLER
# ════════════════════════════════════════════════════════════════════════════

def _on_voice(audio_path, app_state: dict):
    app_state = app_state or _new_app_state()
    if not audio_path:
        return app_state, _render_current(app_state), None, ""

    try:
        text = transcribe_audio(audio_path)
    except Exception:
        text = ""

    if not text:
        return app_state, _render_current(app_state), None, ""

    new_state, html, audio = _handle_action(app_state, {"cmd": "action", "text": text})
    return new_state, html, audio, text


# ════════════════════════════════════════════════════════════════════════════
# GRADIO APP
# ════════════════════════════════════════════════════════════════════════════

_GLOBAL_CSS = """
.gradio-container {
    background: #03060a !important;
    margin: 0 !important;
    padding: 0 !important;
    max-width: 100% !important;
    min-height: 100vh !important;
}
.gradio-container > .main, .gradio-container > .main > .wrap {
    min-height: 100vh !important;
}
footer { display: none !important; }
.gr-prose { display: none !important; }
#sq-bridge-row { display: none !important; }
#sq-voice-row { max-width: 100% !important; padding: 8px 20px !important; }
.gradio-container .prose { display: none !important; }
"""

with gr.Blocks(css=_GLOBAL_CSS, title="SNAPQUEST", head=_SQ_HEAD_JS) as demo:
    app_state = gr.State(_new_app_state())

    main_html = gr.HTML(screen1_html([]))

    # Hidden bridge: JS writes JSON command here, then clicks the button
    with gr.Row(elem_id="sq-bridge-row"):
        cmd_box = gr.Textbox(label="cmd", elem_id="sq-cmd-box")
        cmd_btn = gr.Button("send", elem_id="sq-cmd-btn")

    # Voice — small visible row at the bottom
    with gr.Row(elem_id="sq-voice-row"):
        voice_input = gr.Audio(
            sources=["microphone"], type="filepath",
            label="Voice Action (record, then it auto-submits)",
        )
        voice_output = gr.Audio(label="DM Voice", autoplay=True, visible=True)
        transcribed = gr.Textbox(label="Transcribed", visible=True)

    # ── Wire the bridge ────────────────────────────────────────────────────
    cmd_btn.click(
        _dispatch,
        inputs=[cmd_box, app_state],
        outputs=[app_state, main_html, voice_output],
        api_name=False,
    )

    # ── Voice wiring ───────────────────────────────────────────────────────
    voice_input.stop_recording(
        _on_voice,
        inputs=[voice_input, app_state],
        outputs=[app_state, main_html, voice_output, transcribed],
        api_name=False,
    )