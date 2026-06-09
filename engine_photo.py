"""Photo-based SnapQuest dungeon engine — fixed DM prompt + placeholder filter."""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from vision import analyze_scene

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5vl:3b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
HISTORY_WINDOW = 6

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

DM_SYSTEM_PROMPT = """You are a Dungeon Master narrating a dark fantasy adventure set inside a real room.

STRICT FORMAT — output EXACTLY this, nothing else:
SCENE: [2 atmospheric sentences describing what the character sees]
STORY: [2 sentences describing what just happened from the player action]
CHOICE:
1. [a real action mentioning a specific object from REAL OBJECTS list]
2. [a different real action mentioning a specific object from REAL OBJECTS list]
3. [a third real action]

CHOICE RULES — NEVER output placeholder text like "[specific action]" or "[action here]".
Write real actions. Examples of GOOD choices:
  "Search behind the red chair for clues"
  "Examine the black backpack for supplies"
  "Use the dagger to pry open the window"
Examples of BAD choices (forbidden):
  "[specific action referencing a real object]"
  "[action]"

Keep total response under 120 words. Never break character."""


def _normalize_character_class(character_class: str) -> str:
    lookup = {k.lower(): k for k in STARTING_INVENTORY}
    normalized = lookup.get(character_class.strip().lower())
    if not normalized:
        raise ValueError(f"Unknown character class '{character_class}'.")
    return normalized


def start_photo_game(image_path: str, character_class: str) -> dict[str, Any]:
    class_name = _normalize_character_class(character_class)
    photo_scene = analyze_scene(image_path, class_name)

    return {
        "hp": 100,
        "max_hp": 100,
        "inventory": STARTING_INVENTORY[class_name].copy(),
        "turn": 0,
        "history": [],
        "current_scene": photo_scene["scene_description"],
        "current_choices": photo_scene["choices"],
        "world": "photo",
        "character_class": class_name,
        "photo_scene": photo_scene,
        "quests": [],
        "ascii_art": "",
        "last_parsed": {},
    }


def take_photo_action(state: dict[str, Any], player_action: str) -> tuple[dict[str, Any], dict[str, Any]]:
    updated_state = deepcopy(state)
    prompt = _build_dm_prompt(updated_state, player_action.strip())
    raw_text = _call_dm(prompt)
    parsed = parse_dm_response(raw_text)

    updated_state["turn"] = int(updated_state.get("turn", 0)) + 1
    updated_state["current_scene"] = parsed.get("scene", updated_state.get("current_scene", ""))
    updated_state["current_choices"] = parsed.get("choices", GENERIC_CHOICES)
    updated_state["last_parsed"] = parsed

    history = list(updated_state.get("history", []))
    history.append({"turn": updated_state["turn"], "action": player_action.strip(), "response": parsed})
    updated_state["history"] = history[-HISTORY_WINDOW:]

    return updated_state, parsed


def _build_dm_prompt(state: dict[str, Any], player_action: str) -> str:
    photo_scene = state.get("photo_scene", {})
    class_name = state.get("character_class", "Swordsman")
    class_tone = CLASS_TONES.get(class_name, CLASS_TONES["Swordsman"])
    inv_str = ", ".join(state.get("inventory", [])) or "nothing"
    scene_name = photo_scene.get("scene_name", "Unknown Location")
    objects = photo_scene.get("objects_found", [])
    objects_str = ", ".join(objects) if objects else "unknown objects"
    turn_num = state.get("turn", 0) + 1

    lines = [
        DM_SYSTEM_PROMPT, "",
        f"LOCATION: {scene_name}",
        f"REAL OBJECTS IN THIS PLACE: {objects_str}",
        f"CHARACTER: {class_name} — {class_tone}",
        f"TURN {turn_num} | HP: {state.get('hp', 100)} | INVENTORY: {inv_str}",
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


def _call_dm(prompt: str) -> str:
    """Call Groq if GROQ_API_KEY is set, otherwise fall back to local Ollama."""
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        return _call_groq(prompt, groq_key)
    return _call_ollama(prompt)


def _call_groq(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 300,
    }).encode("utf-8")

    request = Request(
        GROQ_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Groq request failed: {exc}") from exc


def _call_ollama(prompt: str) -> str:
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 300},
    }).encode("utf-8")

    request = Request(OLLAMA_URL, data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8")).get("response", "")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def parse_dm_response(raw: str) -> dict[str, Any]:
    result: dict[str, Any] = {"scene": "", "story": "", "choices": list(GENERIC_CHOICES), "raw": raw}

    scene_match = re.search(r"SCENE\s*:\s*(.+?)(?=STORY\s*:|CHOICE\s*:|$)", raw, re.IGNORECASE | re.DOTALL)
    if scene_match:
        result["scene"] = scene_match.group(1).strip()

    story_match = re.search(r"STORY\s*:\s*(.+?)(?=CHOICE\s*:|SCENE\s*:|$)", raw, re.IGNORECASE | re.DOTALL)
    if story_match:
        result["story"] = story_match.group(1).strip()

    choice_block = re.search(r"CHOICE\s*:\s*(.+?)$", raw, re.IGNORECASE | re.DOTALL)
    if choice_block:
        numbered = re.findall(r"^\s*[1-3][\.\)]\s*(.+)", choice_block.group(1), re.MULTILINE)
        real = [c.strip() for c in numbered
                if "[" not in c and len(c.strip()) > 8]
        if real:
            while len(real) < 3:
                real.append(GENERIC_CHOICES[len(real)])
            result["choices"] = real[:3]

    if not result["scene"] and not result["story"]:
        result["story"] = raw.strip()
        result["choices"] = list(GENERIC_CHOICES)

    return result