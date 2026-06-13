"""engine_photo.py — SnapQuest dungeon engine.

DM backend priority (automatic, no manual config needed):
  1. HF_TOKEN env var present  → HF Inference API (Qwen/Qwen2.5-3B-Instruct, free)
  2. No token                  → Same HF Inference serverless endpoint (free tier, no auth)
  3. Both fail                 → Rule-based fallback (always playable)

Multi-room support via dungeon.py.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from copy import deepcopy
from typing import Any

from vision import analyze_scene
from dungeon import (
    build_rooms, current_room, can_advance, advance_room,
    apply_combat, minimap_html, xp_bar_html,
)

# ── HF Inference API (free serverless) ─────────────────────────────────────
HF_API_URL  = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-3B-Instruct"
HF_TIMEOUT  = 45
HISTORY_WINDOW = 6

# ── Class config ────────────────────────────────────────────────────────────
STARTING_INVENTORY: dict[str, list[str]] = {
    "Swordsman": ["Iron Sword", "Shield", "Torch"],
    "Archer":    ["Longbow", "Quiver", "Rope"],
    "Healer":    ["Staff", "Healing Herbs", "Lantern"],
    "Rogue":     ["Dagger", "Lockpick", "Smoke Bomb"],
    "Mage":      ["Spellbook", "Crystal Orb", "Candle"],
}

CLASS_TONES: dict[str, str] = {
    "Swordsman": "You see defensible positions, chokepoints, and threats in every shadow.",
    "Archer":    "You calculate sightlines, distances, and elevated vantage points.",
    "Healer":    "You sense life energy, danger, and what needs tending.",
    "Rogue":     "You see shadows, hidden passages, and things of value.",
    "Mage":      "You read magical residue in objects; ordinary things reveal arcane secrets.",
}

GENERIC_CHOICES = [
    "Look around carefully",
    "Move forward cautiously",
    "Hold your position and listen",
]

DM_SYSTEM = """You are a Dungeon Master narrating a dark fantasy adventure set inside a real room.

Output EXACTLY this format, nothing else:
SCENE: [2 atmospheric sentences]
STORY: [2 sentences about what just happened]
CHOICE:
1. [action mentioning a real object]
2. [different action mentioning a real object]
3. [third action]

RULES: Never write placeholder text like "[action]". Keep under 120 words. Stay in character."""


# ── Normalisation ───────────────────────────────────────────────────────────

def _norm_class(character_class: str) -> str:
    lu = {k.lower(): k for k in STARTING_INVENTORY}
    out = lu.get(character_class.strip().lower())
    if not out:
        raise ValueError(f"Unknown class '{character_class}'.")
    return out


# ── Game start ──────────────────────────────────────────────────────────────

def start_photo_game(
    image_paths: list[str],
    character_class: str,
) -> dict[str, Any]:
    """Start a new game with 1–3 photos. Each photo = one dungeon room."""
    class_name = _norm_class(character_class)

    # Analyse every photo via vision.py (Modal/MiniCPM-V or fallback)
    photo_scenes: list[dict[str, Any]] = []
    for path in image_paths:
        scene = analyze_scene(path, class_name)
        # Attach atmosphere if missing (vision fallback doesn't always include it)
        if "atmosphere" not in scene:
            scene["atmosphere"] = scene.get("scene_description", "")
        photo_scenes.append(scene)

    rooms = build_rooms(photo_scenes)
    first_room = rooms[0]
    first_room["visited"] = True

    state: dict[str, Any] = {
        # Player
        "hp":              100,
        "max_hp":          100,
        "xp":              0,
        "inventory":       STARTING_INVENTORY[class_name].copy(),
        "character_class": class_name,
        # Dungeon
        "rooms":           rooms,
        "room_index":      0,
        # Turn tracking
        "turn":            0,
        "history":         [],
        # Compat with ui_photo
        "photo_scene":     first_room,   # alias for objects_html etc.
        "current_scene":   first_room["scene_description"],
        "current_choices": first_room["choices"],
        "quests":          [],
        "world":           "photo",
        "last_parsed":     {},
    }
    return state


# ── Action ──────────────────────────────────────────────────────────────────

def take_photo_action(
    state: dict[str, Any],
    player_action: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Process one player action. Returns (new_state, parsed_dm_response)."""
    updated = deepcopy(state)

    # Check for room-advance command first
    action_lower = player_action.strip().lower()
    advance_keywords = {"advance", "next room", "go deeper", "move on",
                        "enter next", "proceed", "deeper"}
    is_advance = any(kw in action_lower for kw in advance_keywords)

    if is_advance and can_advance(updated):
        updated = advance_room(updated)
        room = current_room(updated)
        # Update photo_scene alias
        updated["photo_scene"]     = room
        updated["current_scene"]   = room["scene_description"]
        updated["current_choices"] = room["choices"]

        intro_text = ""
        if room.get("is_boss") and room.get("boss"):
            intro_text = "\n\n" + room["boss"]["intro"]

        parsed: dict[str, Any] = {
            "scene":   room["scene_description"] + intro_text,
            "story":   f"You enter {room['scene_name']}. The air changes.",
            "choices": room["choices"],
            "raw":     "",
        }
    else:
        # Normal DM action
        prompt  = _build_prompt(updated, player_action.strip())
        raw_text = _call_dm(prompt)
        parsed   = parse_dm_response(raw_text)

        # Lightweight combat resolution
        updated, combat_msg = apply_combat(updated, player_action)
        if combat_msg:
            parsed["story"] = (parsed.get("story") or "") + combat_msg

        # Auto-advance choices if room was just cleared
        room = current_room(updated)
        if room.get("cleared") and can_advance(updated):
            parsed["choices"] = parsed.get("choices", list(GENERIC_CHOICES))
            if "Go deeper" not in parsed["choices"]:
                parsed["choices"][-1] = "Go deeper into the dungeon"

        updated["current_scene"]   = parsed.get("scene", updated.get("current_scene", ""))
        updated["current_choices"] = parsed.get("choices", GENERIC_CHOICES)
        updated["photo_scene"]     = current_room(updated)

    updated["turn"] = int(updated.get("turn", 0)) + 1
    updated["last_parsed"] = parsed

    history = list(updated.get("history", []))
    history.append({
        "turn":     updated["turn"],
        "action":   player_action.strip(),
        "response": parsed,
    })
    updated["history"] = history[-HISTORY_WINDOW:]

    return updated, parsed


# ── Prompt builder ──────────────────────────────────────────────────────────

def _build_prompt(state: dict[str, Any], player_action: str) -> str:
    room       = current_room(state)
    class_name = state.get("character_class", "Swordsman")
    inv_str    = ", ".join(state.get("inventory", [])) or "nothing"
    objects    = room.get("objects_found", [])
    obj_str    = ", ".join(objects) if objects else "unknown objects"
    turn_num   = state.get("turn", 0) + 1
    difficulty = room.get("difficulty", "normal").upper()
    is_boss    = room.get("is_boss", False)
    boss_name  = room.get("boss", {}).get("name", "") if is_boss else ""

    lines = [
        DM_SYSTEM, "",
        f"LOCATION: {room.get('scene_name', 'Unknown')}  [DIFFICULTY: {difficulty}]",
    ]
    if is_boss and boss_name:
        boss_hp = room.get("boss", {}).get("hp", "?")
        boss_max = room.get("boss", {}).get("max_hp", "?")
        lines.append(f"⚠ BOSS FIGHT: {boss_name} [{boss_hp}/{boss_max} HP]")
    lines += [
        f"REAL OBJECTS: {obj_str}",
        f"CHARACTER: {class_name} — {CLASS_TONES.get(class_name, '')}",
        f"TURN {turn_num} | HP: {state.get('hp', 100)} | INV: {inv_str}",
        "",
    ]

    for entry in state.get("history", [])[-HISTORY_WINDOW:]:
        lines.append(f"Player: {entry.get('action', '')}")
        resp = entry.get("response", {})
        dm_text = (resp.get("scene", "") + " " + resp.get("story", "")).strip()
        if dm_text:
            lines.append(f"DM: {dm_text}")
        lines.append("")

    lines.append(f"Player: {player_action}")
    lines.append("DM:")
    return "\n".join(lines)


# ── DM caller ───────────────────────────────────────────────────────────────

def _call_dm(prompt: str) -> str:
    """Try HF Inference API (free), fall back to rule-based on any failure."""
    try:
        return _call_hf_inference(prompt)
    except Exception as exc:
        print(f"[engine] HF Inference failed ({exc}), using rule-based fallback.")
        return _rule_based_dm(prompt)


def _call_hf_inference(prompt: str) -> str:
    """HF serverless inference — free, works on HF Spaces without any secret."""
    headers = {"Content-Type": "application/json"}
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = json.dumps({
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.75,
            "return_full_text": False,
            "stop": ["Player:", "---"],
        },
    }).encode("utf-8")

    req = urllib.request.Request(HF_API_URL, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=HF_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HF Inference HTTP {e.code}: {body[:200]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"HF Inference network error: {e.reason}") from e

    # HF returns a list: [{"generated_text": "..."}]
    if isinstance(data, list) and data:
        return data[0].get("generated_text", "")
    # Some models return dict with "error" on loading
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"HF Inference model error: {data['error']}")
    return str(data)


def _rule_based_dm(prompt: str) -> str:
    """Always-works fallback — extracts objects from prompt, generates valid DM text."""
    obj_match = re.search(r"REAL OBJECTS:\s*(.+)", prompt)
    objects   = [o.strip() for o in obj_match.group(1).split(",")] if obj_match else ["the shadows"]

    action_match = re.search(r"Player:\s*(.+)\nDM:", prompt)
    action = action_match.group(1).strip() if action_match else "proceed"

    obj1 = objects[0] if len(objects) > 0 else "the darkness"
    obj2 = objects[1] if len(objects) > 1 else "the walls"
    obj3 = objects[2] if len(objects) > 2 else "the floor"

    return (
        f"SCENE: The chamber feels heavier after your last move. "
        f"The {obj1} looms before you, casting strange shadows.\n"
        f"STORY: You {action.lower()} and discover something unexpected near the {obj2}. "
        f"The dungeon shifts around you.\n"
        f"CHOICE:\n"
        f"1. Examine the {obj1} more closely\n"
        f"2. Search behind the {obj2} for hidden passages\n"
        f"3. Use the {obj3} to your advantage"
    )


# ── Parser ───────────────────────────────────────────────────────────────────

def parse_dm_response(raw: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "scene": "", "story": "", "choices": list(GENERIC_CHOICES), "raw": raw,
    }

    scene_m = re.search(r"SCENE\s*:\s*(.+?)(?=STORY\s*:|CHOICE\s*:|$)", raw, re.IGNORECASE | re.DOTALL)
    if scene_m:
        result["scene"] = scene_m.group(1).strip()

    story_m = re.search(r"STORY\s*:\s*(.+?)(?=CHOICE\s*:|SCENE\s*:|$)", raw, re.IGNORECASE | re.DOTALL)
    if story_m:
        result["story"] = story_m.group(1).strip()

    choice_m = re.search(r"CHOICE\s*:\s*(.+?)$", raw, re.IGNORECASE | re.DOTALL)
    if choice_m:
        numbered = re.findall(r"^\s*[1-3][\.\)]\s*(.+)", choice_m.group(1), re.MULTILINE)
        real = [c.strip() for c in numbered if "[" not in c and len(c.strip()) > 6]
        if real:
            while len(real) < 3:
                real.append(GENERIC_CHOICES[len(real)])
            result["choices"] = real[:3]

    if not result["scene"] and not result["story"]:
        result["story"] = raw.strip()
        result["choices"] = list(GENERIC_CHOICES)

    return result