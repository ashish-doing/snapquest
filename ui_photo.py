"""ui_photo.py — SnapQuest UI.

Changes over v1:
- Multi-photo input (1–3 images) → multi-room dungeon
- Boss room detection + dramatic boss intro screen
- Minimap + XP bar from dungeon.py
- Pixel font (Press Start 2P) loaded via @import
- All original CSS variables, character art, voice wiring preserved
"""
from __future__ import annotations

import html as html_module
import gradio as gr

from engine_photo import start_photo_game, take_photo_action
from dungeon import current_room, can_advance, minimap_html, xp_bar_html
from voice import clean_for_speech, speak, transcribe_audio

CHARACTER_CLASSES = ["Swordsman", "Archer", "Healer", "Rogue", "Mage"]

PIXEL_CHARS = {
    "Swordsman": """ O\n/|\\\n/ \\\n[###]\n|   |\n | |""",
    "Archer":    """ O\n\\|>\n |\n/|\n/ \\""",
    "Healer":    """ O\n+-+-+\n| + |\n+-+-+\n / \\""",
    "Rogue":     """ _O_\n/ | \\\n  |>>\n / \\""",
    "Mage":      """ O\n*\\|/*\n  |\n /|\\\n* / \\*""",
}

# ── CSS ──────────────────────────────────────────────────────────────────────

CHRONOQUEST_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

:root {
    --crt-bg: #090b0f;
    --crt-panel: #101820;
    --crt-green: #8cff9b;
    --crt-amber: #ffd36a;
    --crt-red: #ff6b6b;
    --crt-text: #e8ffe8;
    --crt-muted: #9cb9a3;
    --crt-border: #31513a;
    --pixel: 'Press Start 2P', 'Courier New', monospace;
}

.gradio-container {
    background:
        linear-gradient(rgba(255,255,255,0.025) 50%, rgba(0,0,0,0.04) 50%),
        radial-gradient(circle at center, #17211b 0%, var(--crt-bg) 68%) !important;
    background-size: 100% 4px, 100% 100% !important;
    color: var(--crt-text) !important;
    font-family: 'Courier New', monospace !important;
}

.snapquest-header {
    border: 1px solid var(--crt-border);
    background: linear-gradient(90deg, #0d1513 0%, #111e17 50%, #0d1513 100%);
    padding: 16px 20px;
    box-shadow: inset 0 0 24px rgba(140,255,155,0.08);
    display: flex; align-items: center; justify-content: space-between;
}

.snapquest-title {
    font-family: var(--pixel) !important;
    color: var(--crt-green);
    font-size: 22px;
    font-weight: 800;
    margin: 0;
    text-shadow: 0 0 16px rgba(140,255,155,0.8), 0 0 32px rgba(140,255,155,0.4);
    letter-spacing: 0.05em;
}

.snapquest-subtitle {
    color: var(--crt-muted);
    font-size: 11px;
    margin-top: 6px;
    letter-spacing: 0.12em;
    font-family: 'Courier New', monospace;
}

.snapquest-badges { display: flex; gap: 8px; flex-wrap: wrap; }

.badge {
    border: 1px solid var(--crt-border);
    padding: 3px 8px;
    font-size: 10px;
    color: var(--crt-muted);
    letter-spacing: 0.1em;
    font-family: 'Courier New', monospace;
}

.crt-panel {
    border: 1px solid var(--crt-border) !important;
    background: rgba(16,24,32,0.94) !important;
    box-shadow: inset 0 0 16px rgba(140,255,155,0.05);
}

.story-feed {
    min-height: 340px; max-height: 480px;
    overflow-y: auto; white-space: pre-wrap;
    line-height: 1.6; font-size: 13px !important;
    font-family: 'Courier New', monospace !important;
}

.choice-button button {
    min-height: 56px !important;
    white-space: normal !important;
    border-radius: 2px !important;
    font-family: 'Courier New', monospace !important;
    font-size: 12px !important;
    transition: all 0.2s !important;
    border: 1px solid var(--crt-border) !important;
}

.choice-button button:hover {
    background: rgba(140,255,155,0.08) !important;
    border-color: var(--crt-green) !important;
    box-shadow: 0 0 12px rgba(140,255,155,0.2) !important;
    color: var(--crt-green) !important;
}

/* BOSS button — red glow */
.boss-choice button {
    border-color: #ff6b6b !important;
    color: #ff6b6b !important;
}
.boss-choice button:hover {
    background: rgba(255,107,107,0.1) !important;
    box-shadow: 0 0 16px rgba(255,107,107,0.3) !important;
}

.hp-wrap {
    border: 1px solid var(--crt-border);
    padding: 8px 10px; background: #0b1114;
}

.hp-fill {
    height: 12px;
    background: linear-gradient(90deg, var(--crt-red) 0%, var(--crt-amber) 50%, var(--crt-green) 100%);
    transition: width 0.5s ease;
}

.char-display {
    background: #070f0b;
    border: 1px solid var(--crt-border);
    padding: 12px; text-align: center;
    font-family: 'Courier New', monospace;
    color: var(--crt-green); white-space: pre;
    font-size: 18px; line-height: 1.3;
    text-shadow: 0 0 6px rgba(140,255,155,0.5);
    min-height: 120px; display: flex;
    align-items: center; justify-content: center;
}

/* Boss announcement banner */
.boss-banner {
    border: 2px solid #ff6b6b;
    background: linear-gradient(90deg, #1a0000, #2a0808, #1a0000);
    padding: 16px; text-align: center;
    animation: bossGlow 1.5s infinite alternate;
    margin-bottom: 8px;
}
@keyframes bossGlow {
    from { box-shadow: 0 0 16px rgba(255,107,107,0.3); }
    to   { box-shadow: 0 0 40px rgba(255,107,107,0.7); }
}

.world-photo img {
    object-fit: cover !important; width: 100% !important;
    height: 200px !important; border: 1px solid var(--crt-border);
}

.detected-objects {
    background: #070f0b;
    border: 1px solid var(--crt-border); border-top: none;
    padding: 8px 12px; font-size: 12px;
    color: var(--crt-amber); letter-spacing: 0.05em;
}

textarea, input, select {
    background: #07100d !important; color: var(--crt-text) !important;
    border-color: var(--crt-border) !important;
    font-family: 'Courier New', monospace !important;
}

/* Multi-photo upload area */
.photo-upload-area {
    border: 1px dashed var(--crt-border);
    padding: 10px; background: #070f0b;
    margin-bottom: 4px;
}

.photo-label {
    color: var(--crt-amber); font-size: 11px;
    letter-spacing: 0.1em; margin-bottom: 6px;
    font-family: 'Courier New', monospace;
}

.room-indicator {
    font-family: var(--pixel) !important;
    font-size: 10px; color: var(--crt-amber);
    text-align: center; padding: 6px;
    border: 1px solid var(--crt-border);
    background: #0b1114; letter-spacing: 0.1em;
    margin-bottom: 6px;
}
"""

# ── Onboarding ────────────────────────────────────────────────────────────────

ONBOARDING_HTML = """
<div id="cq-guide" style="
    position:fixed;inset:0;background:rgba(0,0,0,0.97);
    z-index:99999;display:flex;align-items:center;justify-content:center;
    font-family:Courier New,monospace;overflow-y:auto;">
  <div style="
      border:1px solid #4a9e4a;max-width:620px;width:90%;
      padding:40px;background:#080f0b;
      box-shadow:0 0 60px rgba(74,158,74,0.15);margin:20px auto;">

    <div style="color:#8cff9b;font-size:28px;margin-bottom:4px;letter-spacing:0.1em;
                font-family:'Courier New',monospace;font-weight:900;">
      ⚔ SNAPQUEST
    </div>
    <div style="color:#4a9e4a;font-size:11px;letter-spacing:0.3em;margin-bottom:28px;">
      YOUR WORLD · YOUR DUNGEON · MINICPM-V 4.6 · 1.3B
    </div>

    <div style="color:#9cb9a3;font-size:14px;line-height:1.9;margin-bottom:24px;">
      <div style="margin-bottom:12px;">
        <span style="color:#8cff9b;">① UPLOAD 1–3 PHOTOS</span><br>
        <span style="color:#6a8a72;padding-left:16px;">
          Each photo becomes a dungeon room. 3 photos = Entry Hall + Inner Chamber + Boss Lair.
        </span>
      </div>
      <div style="margin-bottom:12px;">
        <span style="color:#8cff9b;">② PICK YOUR CLASS</span><br>
        <span style="color:#6a8a72;padding-left:16px;">
          Rogue sees shadows. Mage sees arcane energy. Same room, different dungeon.
        </span>
      </div>
      <div style="margin-bottom:12px;">
        <span style="color:#8cff9b;">③ FIGHT THROUGH THE ROOMS</span><br>
        <span style="color:#6a8a72;padding-left:16px;">
          Clear each room by attacking enemies. Say "Go deeper" to advance.
        </span>
      </div>
      <div>
        <span style="color:#ff6b6b;">☠ DEFEAT THE FINAL BOSS</span><br>
        <span style="color:#6a8a72;padding-left:16px;">
          The most prominent object in your last photo BECOMES the boss. Destroy it to win.
        </span>
      </div>
    </div>

    <div style="border:1px solid #1e3a1e;padding:14px;margin-bottom:24px;background:rgba(74,158,74,0.04);">
      <div style="color:#4a9e4a;font-size:11px;letter-spacing:0.2em;margin-bottom:8px;">▸ EXAMPLE</div>
      <div style="color:#9cb9a3;font-size:13px;line-height:1.8;">
        Photo 1 (Living room) → <span style="color:#ffd36a;">Entry Hall of Forgotten Steps</span><br>
        Photo 2 (Study) → <span style="color:#ffd36a;">Inner Chamber of Lost Knowledge</span><br>
        Photo 3 (Bedroom) → <span style="color:#ff6b6b;">☠ The Pillow Guardian — BOSS</span>
      </div>
    </div>

    <button
      onclick="document.getElementById('cq-guide').style.display='none'"
      style="background:linear-gradient(90deg,#6b0000,#8b0000);
        color:#c8a96e;border:1px solid #cc0000;
        font-family:Courier New,monospace;font-size:18px;
        padding:16px 32px;cursor:pointer;letter-spacing:0.15em;
        box-shadow:0 0 24px rgba(139,0,0,0.6);width:100%;
        transition:all 0.2s;"
      onmouseover="this.style.boxShadow='0 0 40px rgba(204,0,0,0.8)'"
      onmouseout="this.style.boxShadow='0 0 24px rgba(139,0,0,0.6)'">
      ▶ &nbsp; ENTER THE DUNGEON
    </button>
  </div>
</div>
"""


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _hp_html(state: dict | None) -> str:
    hp = max_hp = 100
    if state:
        hp     = int(state.get("hp", 100))
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
        f'<div class="char-display"><div>'
        f'<div style="font-size:10px;color:var(--crt-muted);letter-spacing:0.2em;margin-bottom:8px;">'
        f'▸ {class_name.upper()}</div>'
        f'<pre style="margin:0;font-size:20px;line-height:1.4;">{art}</pre>'
        f'</div></div>'
    )


def _objects_html(state: dict | None) -> str:
    if not state:
        return ""
    room    = current_room(state) if state.get("rooms") else {}
    objects = room.get("objects_found", [])
    if not objects:
        return ""
    tags = " · ".join(f"[{o}]" for o in objects)
    is_boss = room.get("is_boss", False)
    color   = "var(--crt-red)" if is_boss else "var(--crt-amber)"
    prefix  = "☠ BOSS ROOM — " if is_boss else "▸ DETECTED: "
    return f'<div class="detected-objects" style="color:{color};">{prefix}{tags}</div>'


def _boss_banner_html(state: dict | None) -> str:
    """Returns a pulsing boss banner if the current room is a boss room, else empty."""
    if not state or not state.get("rooms"):
        return ""
    room = current_room(state)
    if not room.get("is_boss") or not room.get("boss"):
        return ""
    boss  = room["boss"]
    b_hp  = boss.get("hp", "?")
    b_max = boss.get("max_hp", "?")
    name  = boss.get("name", "Unknown")
    alive = boss.get("alive", True)
    if not alive:
        return (
            '<div style="border:1px solid #8cff9b;background:#0a1a0a;'
            'padding:12px;text-align:center;color:#8cff9b;font-size:14px;">'
            f'✅ {html_module.escape(name)} DEFEATED!</div>'
        )
    return (
        f'<div class="boss-banner">'
        f'<div style="color:#ff6b6b;font-size:13px;letter-spacing:0.2em;margin-bottom:4px;">'
        f'☠ BOSS ENCOUNTER</div>'
        f'<div style="color:#ffd36a;font-size:16px;font-weight:bold;">'
        f'{html_module.escape(name)}</div>'
        f'<div style="color:#ff6b6b;font-size:12px;margin-top:4px;">'
        f'HP: {b_hp} / {b_max}</div>'
        f'</div>'
    )


def _room_indicator_html(state: dict | None) -> str:
    if not state or not state.get("rooms"):
        return ""
    rooms = state["rooms"]
    idx   = state.get("room_index", 0)
    room  = rooms[min(idx, len(rooms)-1)]
    total = len(rooms)
    label = room.get("label", f"Room {idx+1}")
    name  = room.get("scene_name", "")
    diff  = room.get("difficulty", "").upper()
    color = {"EASY": "#8cff9b", "MEDIUM": "#ffd36a", "HARD": "#ff6b6b"}.get(diff, "#9cb9a3")
    return (
        f'<div class="room-indicator">'
        f'ROOM {idx+1}/{total} · <span style="color:{color};">{label}</span>'
        f'<br><span style="font-size:9px;color:#6a8a72;">{html_module.escape(name)}</span>'
        f'</div>'
    )


def _sidebar_stats_html(state: dict | None) -> str:
    """Combines minimap + XP bar for the left sidebar."""
    if not state or not state.get("rooms"):
        return ""
    return minimap_html(state) + xp_bar_html(state)


def _format_story(state: dict | None, parsed: dict | None = None) -> str:
    if not state or not state.get("rooms"):
        return "Upload 1–3 photos, choose your class, and begin your quest.\n\nThe dungeon awaits."

    room       = current_room(state)
    scene_name = room.get("scene_name", "Unknown Realm")

    lines = [f"═══ {scene_name} ═══", ""]
    lines.append(str(room.get("scene_description", state.get("current_scene", ""))))

    if room.get("is_boss") and room.get("boss") and room["boss"].get("alive"):
        lines.append("")
        lines.append(room["boss"].get("intro", ""))

    if parsed:
        if parsed.get("scene"):
            lines.extend(["", parsed["scene"]])
        if parsed.get("story"):
            lines.extend(["", parsed["story"]])

    history = state.get("history", [])
    if history:
        lines.append("\n─── Chronicle ───")
        for entry in history[-6:]:
            action = entry.get("action", "")
            resp   = entry.get("response", {})
            story  = resp.get("story", "")
            lines.append(f"\n> {action}")
            if story:
                lines.append(story)

    # Advance hint
    from dungeon import can_advance
    if can_advance(state):
        lines.append('\n\n💡 Room cleared — type "Go deeper" to advance!')

    return "\n".join(str(l) for l in lines if l is not None)


def _choice_updates(choices: list[str], is_boss: bool = False) -> list:
    padded = list((choices or [])[:3])
    while len(padded) < 3:
        padded.append("Continue exploring...")
    elem_cls = ["choice-button boss-choice"] * 3 if is_boss else ["choice-button"] * 3
    return [gr.update(value=c, interactive=True, elem_classes=[e]) for c, e in zip(padded, elem_cls)]


def _disabled_choices(label: str = "Start quest first") -> list:
    return [gr.update(value=label, interactive=False) for _ in range(3)]


# ── Event handlers ────────────────────────────────────────────────────────────

def _on_class_change(class_name: str):
    return _char_html(class_name)


def _show_loading(photo1, photo2, photo3):
    photos = [p for p in [photo1, photo2, photo3] if p]
    n = len(photos)
    return (
        f"⚔ The oracle reads your world{'s' if n > 1 else ''}...\n\n"
        f"MiniCPM-V 4.6 is analyzing {n} photo{'s' if n > 1 else ''} on Modal GPU.\n"
        f"{'3 rooms' if n == 3 else '2 rooms' if n == 2 else '1 room (boss)'} will be built.\n"
        f"This takes ~30 seconds on first run."
    )


def _start_game(photo1, photo2, photo3, character_class: str):
    photos = [p for p in [photo1, photo2, photo3] if p]
    if not photos:
        return (
            None, "Please upload at least one photo first.", None, "", "", "",
            _hp_html(None), "No gear yet.", "No quests yet.",
            *_disabled_choices(),
        )
    try:
        state = start_photo_game(photos, character_class)
        room  = current_room(state)
        is_boss = room.get("is_boss", False)
        return (
            state,
            _format_story(state),
            photos[0],
            _objects_html(state),
            _boss_banner_html(state),
            _sidebar_stats_html(state),
            _hp_html(state),
            "\n".join(f"- {i}" for i in state.get("inventory", [])),
            "No quests yet.",
            *_choice_updates(state.get("current_choices", []), is_boss),
        )
    except Exception as exc:
        return (
            None, f"Error: {html_module.escape(str(exc))}", None, "", "", "",
            _hp_html(None), "No gear yet.", "No quests yet.",
            *_disabled_choices("Error — retry"),
        )


def _take_action(state: dict | None, action: str):
    if not state:
        return (
            state, "Start a quest first.", "", "", "",
            _hp_html(None), "No gear yet.", "No quests yet.", None,
            *_disabled_choices(),
        )
    if not action or not action.strip():
        room = current_room(state) if state.get("rooms") else {}
        return (
            state,
            _format_story(state),
            _objects_html(state),
            _boss_banner_html(state),
            _sidebar_stats_html(state),
            _hp_html(state),
            "\n".join(f"- {i}" for i in state.get("inventory", [])),
            "No quests yet.", None,
            *_choice_updates(state.get("current_choices", []), room.get("is_boss", False)),
        )
    try:
        new_state, parsed = take_photo_action(state, action)
        room    = current_room(new_state)
        is_boss = room.get("is_boss", False)
        audio_path = None
        try:
            txt = clean_for_speech(parsed)
            if txt:
                audio_path = speak(txt)
        except Exception:
            pass
        return (
            new_state,
            _format_story(new_state, parsed),
            _objects_html(new_state),
            _boss_banner_html(new_state),
            _sidebar_stats_html(new_state),
            _hp_html(new_state),
            "\n".join(f"- {i}" for i in new_state.get("inventory", [])),
            "No quests yet.",
            audio_path,
            *_choice_updates(new_state.get("current_choices", []), is_boss),
        )
    except Exception as exc:
        room = current_room(state) if state.get("rooms") else {}
        return (
            state,
            f"{_format_story(state)}\n\n⚠ {html_module.escape(str(exc))}",
            _objects_html(state),
            _boss_banner_html(state),
            _sidebar_stats_html(state),
            _hp_html(state),
            "\n".join(f"- {i}" for i in state.get("inventory", [])),
            "No quests yet.", None,
            *_choice_updates(state.get("current_choices", []), room.get("is_boss", False)),
        )


def _submit_text(state, text):
    return _take_action(state, text or "")


def _submit_voice(audio_path, state):
    if not audio_path:
        result = _take_action(state, "")
        return (*result, "")
    transcribed = transcribe_audio(audio_path)
    result = _take_action(state, transcribed)
    return (*result, transcribed)


# ── Layout ────────────────────────────────────────────────────────────────────

with gr.Blocks(css=CHRONOQUEST_CSS, title="SNAPQUEST") as demo:
    game_state = gr.State({})

    gr.HTML(ONBOARDING_HTML)

    # Header
    gr.HTML("""
    <div class="snapquest-header">
      <div>
        <h1 class="snapquest-title">⚔ SNAPQUEST</h1>
        <div class="snapquest-subtitle">
          Photo-to-RPG · MiniCPM-V 4.6 · 1.3B params · your world, your dungeon
        </div>
      </div>
      <div class="snapquest-badges">
        <span class="badge">🦙 MiniCPM-V 4.6</span>
        <span class="badge">⚡ MODAL GPU</span>
        <span class="badge">🎤 VOICE</span>
        <span class="badge">🗺 MULTI-ROOM</span>
        <span class="badge">☠ BOSS FIGHT</span>
      </div>
    </div>
    """)

    with gr.Row():
        # ── LEFT: Setup sidebar ──────────────────────────────────────────────
        with gr.Column(scale=1, elem_classes=["crt-panel"]):

            # Multi-photo upload
            gr.HTML('<div class="photo-label">📷 UPLOAD PHOTOS (1–3) · Each = 1 Dungeon Room</div>')
            photo1 = gr.Image(type="filepath", label="Room 1 — Entry Hall", height=120)
            photo2 = gr.Image(type="filepath", label="Room 2 — Inner Chamber (optional)", height=120)
            photo3 = gr.Image(type="filepath", label="Room 3 — Boss Lair (optional)", height=120)

            character_class = gr.Radio(
                choices=CHARACTER_CLASSES, value="Swordsman", label="Character Class",
            )
            char_display = gr.HTML(_char_html("Swordsman"))
            start_button = gr.Button("⚔ BEGIN QUEST", variant="primary")

            # Stats sidebar
            sidebar_stats = gr.HTML("")
            hp_bar        = gr.HTML(_hp_html(None))
            inventory_box = gr.Textbox(
                label="Inventory", lines=5, interactive=False, value="No gear yet.",
            )
            quests_box = gr.Textbox(
                label="Quests", lines=3, interactive=False, value="No quests yet.",
            )

        # ── CENTER: Game area ────────────────────────────────────────────────
        with gr.Column(scale=2):
            boss_banner   = gr.HTML("")
            room_indicator = gr.HTML("")

            with gr.Row():
                photo_preview = gr.Image(
                    type="filepath", label="Your World",
                    height=200, elem_classes=["world-photo"],
                )
            objects_display = gr.HTML("")

            story_panel = gr.Textbox(
                label="Chronicle Feed",
                value="Upload photos, choose your class, and begin your quest.\n\nThe dungeon awaits.",
                lines=14, interactive=False, elem_classes=["story-feed"],
            )

            with gr.Row():
                choice_1 = gr.Button("Start quest first", elem_classes=["choice-button"], interactive=False)
                choice_2 = gr.Button("Start quest first", elem_classes=["choice-button"], interactive=False)
                choice_3 = gr.Button("Start quest first", elem_classes=["choice-button"], interactive=False)

            with gr.Row():
                text_action = gr.Textbox(
                    label="Custom Action",
                    placeholder='What do you do? (try "attack" or "go deeper")',
                    scale=4,
                )
                submit_text = gr.Button("⚔ Act", scale=1)

        # ── RIGHT: Voice + scene ─────────────────────────────────────────────
        with gr.Column(scale=1, elem_classes=["crt-panel"]):
            ascii_panel = gr.Textbox(
                label="Scene", lines=8, interactive=False, elem_classes=["ascii-panel"],
            )
            voice_input = gr.Audio(
                sources=["microphone"], type="filepath", label="🎙 Voice Input",
            )
            transcribed_text = gr.Textbox(label="Transcribed", interactive=False, lines=2)
            voice_button  = gr.Button("▶ Use Voice Action")
            voice_output  = gr.Audio(label="🔊 DM Voice", autoplay=True)

    # ── Output lists ──────────────────────────────────────────────────────────
    # start_game returns:
    #   state, story, photo_preview, objects, boss_banner, sidebar_stats,
    #   hp_bar, inventory, quests, c1, c2, c3
    start_outputs = [
        game_state, story_panel, photo_preview,
        objects_display, boss_banner, sidebar_stats,
        hp_bar, inventory_box, quests_box,
        choice_1, choice_2, choice_3,
    ]

    # take_action returns:
    #   state, story, objects, boss_banner, sidebar_stats,
    #   hp_bar, inventory, quests, audio, c1, c2, c3
    action_outputs = [
        game_state, story_panel,
        objects_display, boss_banner, sidebar_stats,
        hp_bar, inventory_box, quests_box,
        voice_output,
        choice_1, choice_2, choice_3,
    ]

    # ── Wire events ───────────────────────────────────────────────────────────
    character_class.change(
        _on_class_change, inputs=[character_class], outputs=[char_display], api_name=False,
    )

    start_button.click(
        _show_loading,
        inputs=[photo1, photo2, photo3],
        outputs=[story_panel],
        api_name=False,
    ).then(
        _start_game,
        inputs=[photo1, photo2, photo3, character_class],
        outputs=start_outputs,
        api_name=False,
    )

    choice_1.click(
        lambda s, v: _take_action(s, v),
        inputs=[game_state, choice_1], outputs=action_outputs, api_name=False,
    )
    choice_2.click(
        lambda s, v: _take_action(s, v),
        inputs=[game_state, choice_2], outputs=action_outputs, api_name=False,
    )
    choice_3.click(
        lambda s, v: _take_action(s, v),
        inputs=[game_state, choice_3], outputs=action_outputs, api_name=False,
    )

    submit_text.click(
        _submit_text, inputs=[game_state, text_action], outputs=action_outputs, api_name=False,
    )
    text_action.submit(
        _submit_text, inputs=[game_state, text_action], outputs=action_outputs, api_name=False,
    )

    voice_button.click(
        _submit_voice,
        inputs=[voice_input, game_state],
        outputs=action_outputs + [transcribed_text],
        api_name=False,
    )