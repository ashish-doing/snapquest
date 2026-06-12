"""SnapQuest UI — with onboarding, pixel characters, photo fit fix, class highlight."""

from __future__ import annotations
import html
import gradio as gr
from engine_photo import start_photo_game, take_photo_action
from voice import clean_for_speech, speak, transcribe_audio

CHARACTER_CLASSES = ["Swordsman", "Archer", "Healer", "Rogue", "Mage"]

# Pixel art characters per class
PIXEL_CHARS = {
    "Swordsman": """
  O
 /|\\
 / \\
[###]
|   |
 | |""",
    "Archer": """
  O
 \\|>
  |
 /|
/ \\""",
    "Healer": """
  O
+-+-+
| + |
+-+-+
 / \\""",
    "Rogue": """
 _O_
/ | \\
  |>>
 / \\""",
    "Mage": """
  O
*\\|/*
  |
 /|\\
* / \\*""",
}

CHRONOQUEST_CSS = """
:root {
    --crt-bg: #090b0f;
    --crt-panel: #101820;
    --crt-green: #8cff9b;
    --crt-amber: #ffd36a;
    --crt-red: #ff6b6b;
    --crt-text: #e8ffe8;
    --crt-muted: #9cb9a3;
    --crt-border: #31513a;
}

.gradio-container {
    background:
        linear-gradient(rgba(255,255,255,0.025) 50%, rgba(0,0,0,0.04) 50%),
        radial-gradient(circle at center, #17211b 0%, var(--crt-bg) 68%) !important;
    background-size: 100% 4px, 100% 100% !important;
    color: var(--crt-text) !important;
    font-family: "Courier New", monospace !important;
}

.snapquest-header {
    border: 1px solid var(--crt-border);
    background: linear-gradient(90deg, #0d1513 0%, #111e17 50%, #0d1513 100%);
    padding: 16px 20px;
    box-shadow: inset 0 0 24px rgba(140,255,155,0.08);
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.snapquest-title {
    color: var(--crt-green);
    font-size: 32px;
    font-weight: 800;
    margin: 0;
    text-shadow: 0 0 12px rgba(140,255,155,0.7);
    letter-spacing: 0.05em;
}

.snapquest-subtitle {
    color: var(--crt-muted);
    font-size: 12px;
    margin-top: 4px;
    letter-spacing: 0.1em;
}

.snapquest-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.badge {
    border: 1px solid var(--crt-border);
    padding: 3px 8px;
    font-size: 11px;
    color: var(--crt-muted);
    letter-spacing: 0.1em;
}

.crt-panel {
    border: 1px solid var(--crt-border) !important;
    background: rgba(16,24,32,0.94) !important;
    box-shadow: inset 0 0 16px rgba(140,255,155,0.05);
}

.story-feed {
    min-height: 340px;
    max-height: 480px;
    overflow-y: auto;
    white-space: pre-wrap;
    line-height: 1.5;
    font-size: 14px !important;
}

.choice-button button {
    min-height: 56px !important;
    white-space: normal !important;
    border-radius: 2px !important;
    font-family: "Courier New", monospace !important;
    font-size: 13px !important;
    transition: all 0.2s !important;
}

.choice-button button:hover {
    background: rgba(140,255,155,0.08) !important;
    border-color: var(--crt-green) !important;
    box-shadow: 0 0 12px rgba(140,255,155,0.2) !important;
}

.hp-wrap {
    border: 1px solid var(--crt-border);
    padding: 8px 10px;
    background: #0b1114;
}

.hp-fill {
    height: 12px;
    background: linear-gradient(90deg, var(--crt-red) 0%, var(--crt-amber) 50%, var(--crt-green) 100%);
    transition: width 0.5s ease;
}

.char-display {
    background: #070f0b;
    border: 1px solid var(--crt-border);
    padding: 12px;
    text-align: center;
    font-family: "Courier New", monospace;
    color: var(--crt-green);
    white-space: pre;
    font-size: 18px;
    line-height: 1.3;
    text-shadow: 0 0 6px rgba(140,255,155,0.5);
    min-height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Radio button class highlight */
.gr-radio label {
    cursor: pointer;
    transition: color 0.2s;
}
.gr-radio input[type="radio"]:checked + span,
label:has(input[type="radio"]:checked) span,
label:has(input[type="radio"]:checked) {
    color: var(--crt-green) !important;
    text-shadow: 0 0 8px rgba(140,255,155,0.6) !important;
}

/* Photo display — object-fit cover, no stretch */
.world-photo img {
    object-fit: cover !important;
    width: 100% !important;
    height: 200px !important;
    border: 1px solid var(--crt-border);
}

.detected-objects {
    background: #070f0b;
    border: 1px solid var(--crt-border);
    border-top: none;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--crt-amber);
    letter-spacing: 0.05em;
}

textarea, input, select {
    background: #07100d !important;
    color: var(--crt-text) !important;
    border-color: var(--crt-border) !important;
    font-family: "Courier New", monospace !important;
}
"""

ONBOARDING_HTML = """
<div id="cq-guide" style="
    position:fixed;inset:0;background:rgba(0,0,0,0.95);
    z-index:99999;display:flex;align-items:center;justify-content:center;
    font-family:Courier New,monospace;">
  <div style="
      border:1px solid #4a9e4a;max-width:600px;width:90%;
      padding:44px;background:#080f0b;
      box-shadow:0 0 60px rgba(74,158,74,0.15);">

    <div style="color:#8cff9b;font-size:34px;margin-bottom:4px;letter-spacing:0.08em;">
      ⚔ SNAPQUEST
    </div>
    <div style="color:#4a9e4a;font-size:12px;letter-spacing:0.3em;margin-bottom:32px;text-transform:uppercase;">
      Your World. Your Dungeon. · MiniCPM-V 4.6 · 1.3B Parameters
    </div>

    <div style="color:#9cb9a3;font-size:16px;line-height:2;margin-bottom:28px;">
      <div style="margin-bottom:8px;">
        <span style="color:#8cff9b;font-size:18px;">① UPLOAD PHOTO</span><br>
        <span style="color:#6a8a72;padding-left:20px;">Any real place — your room, desk, or street. The AI reads every object in it.</span>
      </div>
      <div style="margin-bottom:8px;">
        <span style="color:#8cff9b;font-size:18px;">② PICK CLASS</span><br>
        <span style="color:#6a8a72;padding-left:20px;">Swordsman, Archer, Healer, Rogue, or Mage. Each sees the world differently.</span>
      </div>
      <div style="margin-bottom:8px;">
        <span style="color:#8cff9b;font-size:18px;">③ BEGIN QUEST</span><br>
        <span style="color:#6a8a72;padding-left:20px;">Click "Begin Quest". MiniCPM-V 4.6 reads your photo and builds the dungeon inside it.</span>
      </div>
      <div>
        <span style="color:#8cff9b;font-size:18px;">④ PLAY</span><br>
        <span style="color:#6a8a72;padding-left:20px;">Click choices, type custom actions, or speak with your microphone.</span>
      </div>
    </div>

    <div style="border:1px solid #1e3a1e;padding:14px 16px;margin-bottom:28px;
        background:rgba(74,158,74,0.04);">
      <div style="color:#4a9e4a;font-size:12px;letter-spacing:0.2em;margin-bottom:8px;">
        ▸ EXAMPLE TRANSFORMATION
      </div>
      <div style="color:#9cb9a3;font-size:14px;line-height:1.8;">
        Your bookshelf → <span style="color:#ffd36a;">Archive of Ancient Tomes</span><br>
        Your lamp → <span style="color:#ffd36a;">Flickering Oracle</span><br>
        Your window → <span style="color:#ffd36a;">Gateway to the Abyss</span>
      </div>
    </div>

    <div style="color:#3a5a3a;font-size:11px;margin-bottom:20px;letter-spacing:0.1em;">
      BUILT FOR HUGGINGFACE BUILD SMALL HACKATHON 2026 · OPENBMB $10K TRACK · MODAL LABS GPU
    </div>

    <button
      onclick="document.getElementById('cq-guide').style.display='none'"
      style="
        background:linear-gradient(90deg,#6b0000,#8b0000);
        color:#c8a96e;border:1px solid #cc0000;
        font-family:Courier New,monospace;font-size:22px;
        padding:16px 32px;cursor:pointer;letter-spacing:0.15em;
        box-shadow:0 0 24px rgba(139,0,0,0.6);width:100%;
        transition:all 0.2s;"
      onmouseover="this.style.background='linear-gradient(90deg,#8b0000,#cc0000)';this.style.boxShadow='0 0 40px rgba(204,0,0,0.8)'"
      onmouseout="this.style.background='linear-gradient(90deg,#6b0000,#8b0000)';this.style.boxShadow='0 0 24px rgba(139,0,0,0.6)'">
      ▶ &nbsp; ENTER THE DUNGEON
    </button>
  </div>
</div>
"""


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _hp_html(state: dict | None) -> str:
    hp = max_hp = 100
    if state:
        hp = int(state.get("hp", 100))
        max_hp = int(state.get("max_hp", 100))
    pct = max(0, min(100, int((hp / max(max_hp, 1)) * 100)))
    return (
        f'<div class="hp-wrap">'
        f'<div style="color:var(--crt-muted);font-size:12px;letter-spacing:0.1em;">'
        f'HP {hp}/{max_hp}</div>'
        f'<div style="background:#1a0808;margin-top:6px;border:1px solid #3a1414;">'
        f'<div class="hp-fill" style="width:{pct}%"></div></div>'
        f'</div>'
    )


def _char_html(class_name: str) -> str:
    art = PIXEL_CHARS.get(class_name, PIXEL_CHARS["Swordsman"])
    return (
        f'<div class="char-display">'
        f'<div>'
        f'<div style="font-size:11px;color:var(--crt-muted);letter-spacing:0.2em;margin-bottom:8px;">'
        f'▸ {class_name.upper()}</div>'
        f'<pre style="margin:0;font-size:20px;line-height:1.4;">{art}</pre>'
        f'</div>'
        f'</div>'
    )


def _objects_html(state: dict | None) -> str:
    if not state:
        return ""
    objects = state.get("photo_scene", {}).get("objects_found", [])
    if not objects:
        return ""
    tags = " · ".join(f"[{o}]" for o in objects)
    return f'<div class="detected-objects">▸ DETECTED: {tags}</div>'


def _format_story(state: dict | None, parsed: dict | None = None) -> str:
    if not state:
        return "Upload a photo, choose your class, and begin your quest.\n\nThe dungeon awaits."

    photo_scene = state.get("photo_scene", {})
    scene_name = photo_scene.get("scene_name", "Unknown Realm")
    atmosphere = photo_scene.get("atmosphere", "")

    lines = [f"═══ {scene_name} ═══"]
    if atmosphere:
        lines.append(atmosphere)
    lines.append("")
    lines.append(str(state.get("current_scene", "")))

    if parsed and parsed.get("story"):
        lines.extend(["", parsed["story"]])

    history = state.get("history", [])
    if history:
        lines.append("\n─── Chronicle ───")
        for entry in history[-6:]:
            action = entry.get("action", "")
            resp = entry.get("response", {})
            story = resp.get("story", "")
            lines.append(f"\n> {action}")
            if story:
                lines.append(story)

    return "\n".join(line for line in lines if line is not None)


def _choice_updates(choices: list[str]) -> list:
    padded = list((choices or [])[:3])
    while len(padded) < 3:
        padded.append("Continue exploring...")
    return [gr.update(value=c, interactive=True) for c in padded]


def _disabled_choice_updates(label: str = "Start quest first") -> list:
    return [gr.update(value=label, interactive=False) for _ in range(3)]


# ─── HANDLERS ─────────────────────────────────────────────────────────────────

def _on_class_change(class_name: str):
    return _char_html(class_name)


def _show_loading(image_path: str | None):
    return "⚔ The oracle reads your world...\n\nMiniCPM-V 4.6 is analyzing your photo on Modal GPU.\nThis takes ~30 seconds on first run.", image_path


def _start_game(image_path: str | None, character_class: str):
    if not image_path:
        return (None, "Please upload a photo first.", None, "", _hp_html(None),
                "No gear yet.", "No quests yet.", *_disabled_choice_updates())
    try:
        state = start_photo_game(image_path, character_class)
        story = _format_story(state)
        objects_info = _objects_html(state)
        return (
            state, story, image_path, objects_info, _hp_html(state),
            "\n".join(f"- {i}" for i in state.get("inventory", [])),
            "No quests yet.",
            *_choice_updates(state.get("current_choices", [])),
        )
    except Exception as exc:
        return (None, f"Error: {html.escape(str(exc))}", image_path, "",
                _hp_html(None), "No gear yet.", "No quests yet.",
                *_disabled_choice_updates("Error — retry"))


def _take_action(state: dict | None, action: str):
    if not state:
        return (state, "Start a quest first.", "", _hp_html(None),
                "No gear yet.", "No quests yet.", None, *_disabled_choice_updates())
    if not action or not action.strip():
        return (state, _format_story(state), _objects_html(state),
                _hp_html(state),
                "\n".join(f"- {i}" for i in state.get("inventory", [])),
                "No quests yet.", None,
                *_choice_updates(state.get("current_choices", [])))
    try:
        new_state, parsed = take_photo_action(state, action)
        story = _format_story(new_state, parsed)
        audio_path = None
        try:
            txt = clean_for_speech(parsed)
            if txt:
                audio_path = speak(txt)
        except Exception:
            pass
        return (
            new_state, story, _objects_html(new_state), _hp_html(new_state),
            "\n".join(f"- {i}" for i in new_state.get("inventory", [])),
            "No quests yet.", audio_path,
            *_choice_updates(new_state.get("current_choices", [])),
        )
    except Exception as exc:
        return (state, f"{_format_story(state)}\n\n⚠ {html.escape(str(exc))}",
                _objects_html(state), _hp_html(state),
                "\n".join(f"- {i}" for i in state.get("inventory", [])),
                "No quests yet.", None,
                *_choice_updates(state.get("current_choices", [])))


def _submit_text(state, text):
    return _take_action(state, text or "")


def _submit_voice(audio_path, state):
    if not audio_path:
        return (*_take_action(state, ""), "")
    transcribed = transcribe_audio(audio_path)
    return (*_take_action(state, transcribed), transcribed)


# ─── LAYOUT ───────────────────────────────────────────────────────────────────

with gr.Blocks(css=CHRONOQUEST_CSS, title="SNAPQUEST") as demo:
    game_state = gr.State({})

    # Onboarding
    gr.HTML(ONBOARDING_HTML)

    # Header
    gr.HTML("""
    <div class="snapquest-header">
      <div>
        <h1 class="snapquest-title">⚔ SNAPQUEST</h1>
        <div class="snapquest-subtitle">Photo-to-RPG · MiniCPM-V 4.6 · 1.3B params · your world, your dungeon</div>
      </div>
      <div class="snapquest-badges">
        <span class="badge">🔌 OFFLINE</span>
        <span class="badge">🦙 MiniCPM-V 4.6</span>
        <span class="badge">⚡ MODAL GPU</span>
        <span class="badge">🎤 VOICE</span>
      </div>
    </div>
    """)

    with gr.Row():
        # LEFT — setup
        with gr.Column(scale=1, elem_classes=["crt-panel"]):
            photo_input = gr.Image(type="filepath", label="📷 Upload Your Photo")
            character_class = gr.Radio(
                choices=CHARACTER_CLASSES, value="Swordsman", label="Character Class"
            )
            char_display = gr.HTML(_char_html("Swordsman"))
            start_button = gr.Button("⚔ BEGIN QUEST", variant="primary")
            hp_bar = gr.HTML(_hp_html(None))
            inventory_box = gr.Textbox(label="Inventory", lines=4,
                                       interactive=False, value="No gear yet.")
            quests_box = gr.Textbox(label="Quests", lines=3,
                                    interactive=False, value="No quests yet.")

        # CENTER — game
        with gr.Column(scale=2):
            with gr.Row():
                photo_preview = gr.Image(
                    type="filepath", label="Your World",
                    height=200, elem_classes=["world-photo"]
                )
            objects_display = gr.HTML("")
            story_panel = gr.Textbox(
                label="Chronicle Feed",
                value="Upload a photo, choose your class, and begin your quest.\n\nThe dungeon awaits.",
                lines=14, interactive=False, elem_classes=["story-feed"]
            )
            with gr.Row():
                choice_1 = gr.Button("Start quest first", elem_classes=["choice-button"], interactive=False)
                choice_2 = gr.Button("Start quest first", elem_classes=["choice-button"], interactive=False)
                choice_3 = gr.Button("Start quest first", elem_classes=["choice-button"], interactive=False)
            with gr.Row():
                text_action = gr.Textbox(label="Custom Action",
                                         placeholder="What do you do?", scale=4)
                submit_text = gr.Button("⚔ Act", scale=1)

        # RIGHT — voice + scene
        with gr.Column(scale=1, elem_classes=["crt-panel"]):
            ascii_panel = gr.Textbox(label="Scene", lines=8, interactive=False,
                                     elem_classes=["ascii-panel"])
            voice_input = gr.Audio(sources=["microphone"], type="filepath",
                                   label="🎙 Voice Input")
            transcribed_text = gr.Textbox(label="Transcribed",
                                          interactive=False, lines=2)
            voice_button = gr.Button("▶ Use Voice Action")
            voice_output = gr.Audio(label="🔊 DM Voice", autoplay=True)

    # Output lists
    start_outputs = [game_state, story_panel, photo_preview, objects_display,
                     hp_bar, inventory_box, quests_box, choice_1, choice_2, choice_3]

    action_outputs = [game_state, story_panel, objects_display, hp_bar,
                      inventory_box, quests_box, voice_output,
                      choice_1, choice_2, choice_3]

    # Wire events
    character_class.change(_on_class_change, inputs=[character_class], outputs=[char_display], api_name=False)

    start_button.click(
        _show_loading, inputs=[photo_input], outputs=[story_panel, photo_preview], api_name=False
    ).then(
        _start_game, inputs=[photo_input, character_class], outputs=start_outputs, api_name=False
    )

    choice_1.click(lambda s, v: _take_action(s, v),
                   inputs=[game_state, choice_1], outputs=action_outputs, api_name=False)
    choice_2.click(lambda s, v: _take_action(s, v),
                   inputs=[game_state, choice_2], outputs=action_outputs, api_name=False)
    choice_3.click(lambda s, v: _take_action(s, v),
                   inputs=[game_state, choice_3], outputs=action_outputs, api_name=False)

    submit_text.click(_submit_text, inputs=[game_state, text_action], outputs=action_outputs, api_name=False)
    text_action.submit(_submit_text, inputs=[game_state, text_action], outputs=action_outputs, api_name=False)

    voice_button.click(_submit_voice, inputs=[voice_input, game_state],
                       outputs=action_outputs + [transcribed_text], api_name=False)