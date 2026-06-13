"""dungeon.py — Multi-room dungeon manager for SnapQuest.

Each uploaded photo becomes one room. The final room always spawns a BOSS
whose name and abilities are derived from the most prominent object in that photo.
Room 1 is easy, Room 2 is medium, Room 3 (boss) is hard.

No external dependencies beyond what vision.py already uses.
"""
from __future__ import annotations

import random
from typing import Any

# ── Difficulty scaling ──────────────────────────────────────────────────────

ROOM_CONFIG = [
    {"label": "Entry Hall",    "difficulty": "easy",   "enemy_hp": 30,  "xp": 20,  "loot_count": 1},
    {"label": "Inner Chamber", "difficulty": "medium",  "enemy_hp": 60,  "xp": 40,  "loot_count": 2},
    {"label": "Boss Lair",     "difficulty": "hard",   "enemy_hp": 120, "xp": 100, "loot_count": 3},
]

LOOT_POOL = [
    "Ancient Coin", "Healing Potion", "Shadow Cloak", "Enchanted Rope",
    "Glowing Shard", "Iron Key", "Arcane Scroll", "Bone Dagger",
    "Ember Flask", "Thornwood Staff", "Silver Ring", "Rune Stone",
]

BOSS_TITLES = ["Guardian", "Sentinel", "Warden", "Devourer", "Specter", "Revenant"]
BOSS_ATTACKS = [
    "delivers a crushing blow",
    "unleashes a wave of dark energy",
    "sweeps the room with shadow tendrils",
    "lets out a terrifying roar that shakes the walls",
    "channels the room's power into a devastating strike",
]


# ── Boss generation ─────────────────────────────────────────────────────────

def generate_boss(objects_found: list[str]) -> dict[str, Any]:
    """Turn the most prominent object in the final room into a boss."""
    anchor = objects_found[0] if objects_found else "Shadow"
    title  = random.choice(BOSS_TITLES)
    name   = f"The {anchor.title()} {title}"
    hp     = ROOM_CONFIG[2]["enemy_hp"]
    return {
        "name":    name,
        "hp":      hp,
        "max_hp":  hp,
        "attacks": BOSS_ATTACKS,
        "alive":   True,
        "intro":   (
            f"The air grows cold. From the depths of the room, "
            f"{name} rises — the very essence of this place given terrible form. "
            f"Its {random.choice(objects_found[1:] if len(objects_found) > 1 else ['shadow'])} "
            f"pulses with malevolent energy."
        ),
    }


# ── Room builder ────────────────────────────────────────────────────────────

def build_rooms(photo_scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert a list of vision.py scene dicts into dungeon rooms.

    photo_scenes: 1–3 dicts returned by vision.analyze_scene()
    Returns a list of room dicts ready to store in game_state["rooms"].
    """
    rooms: list[dict[str, Any]] = []
    n = len(photo_scenes)

    for i, scene in enumerate(photo_scenes):
        cfg_idx = min(i, 2)          # clamp to 3 configs
        if n == 1:
            cfg_idx = 2              # single photo → straight to boss
        elif n == 2:
            cfg_idx = 0 if i == 0 else 2   # two photos → entry + boss

        cfg  = ROOM_CONFIG[cfg_idx]
        is_boss = (i == n - 1)       # last room is always boss

        room: dict[str, Any] = {
            "index":       i,
            "label":       cfg["label"],
            "difficulty":  cfg["difficulty"],
            "scene_name":  scene.get("scene_name", f"Room {i+1}"),
            "scene_description": scene.get("scene_description", ""),
            "atmosphere":  scene.get("atmosphere", ""),
            "objects_found": scene.get("objects_found", []),
            "choices":     scene.get("choices", []),
            "enemy_hp":    cfg["enemy_hp"],
            "enemy_max_hp": cfg["enemy_hp"],
            "enemy_alive": True,
            "xp_reward":   cfg["xp"],
            "loot":        random.sample(LOOT_POOL, min(cfg["loot_count"], len(LOOT_POOL))),
            "cleared":     False,
            "is_boss":     is_boss,
            "boss":        generate_boss(scene.get("objects_found", ["Shadow"])) if is_boss else None,
            "visited":     False,
        }
        rooms.append(room)

    return rooms


# ── State helpers ───────────────────────────────────────────────────────────

def current_room(state: dict[str, Any]) -> dict[str, Any]:
    rooms = state.get("rooms", [])
    idx   = state.get("room_index", 0)
    return rooms[min(idx, len(rooms) - 1)]


def can_advance(state: dict[str, Any]) -> bool:
    """Player can advance if current room is cleared and there's a next room."""
    room = current_room(state)
    rooms = state.get("rooms", [])
    idx   = state.get("room_index", 0)
    return room.get("cleared", False) and (idx + 1) < len(rooms)


def advance_room(state: dict[str, Any]) -> dict[str, Any]:
    """Move to next room. Returns updated state (mutates in place)."""
    if can_advance(state):
        state["room_index"] += 1
        room = current_room(state)
        room["visited"] = True
    return state


def apply_combat(state: dict[str, Any], action: str) -> tuple[dict[str, Any], str]:
    """
    Very lightweight combat resolution — called from engine_photo after DM narrates.
    Returns (updated_state, combat_message).
    Combat only triggers on attack-flavoured actions.
    """
    ATTACK_KEYWORDS = {"attack", "fight", "strike", "hit", "stab", "slash", "shoot",
                       "cast", "blast", "smash", "punch", "kick", "throw", "use"}
    action_lower = action.lower()
    is_attack = any(kw in action_lower for kw in ATTACK_KEYWORDS)

    room  = current_room(state)
    msg   = ""

    if not is_attack or not room.get("enemy_alive", False):
        return state, msg

    # Player deals 10–25 damage
    player_dmg = random.randint(10, 25)
    # Boss or enemy deals 5–15 damage back
    enemy_dmg  = random.randint(5, 15)

    if room.get("is_boss") and room.get("boss"):
        boss = room["boss"]
        boss["hp"] = max(0, boss["hp"] - player_dmg)
        attack_desc = random.choice(boss["attacks"])
        msg = (
            f"\n⚔ You strike {boss['name']} for {player_dmg} damage! "
            f"[{boss['hp']}/{boss['max_hp']} HP]\n"
            f"💀 {boss['name']} {attack_desc} — you take {enemy_dmg} damage!"
        )
        if boss["hp"] <= 0:
            boss["alive"] = False
            room["enemy_alive"] = False
            room["cleared"] = True
            # Give loot
            loot = room.get("loot", [])
            state["inventory"] = state.get("inventory", []) + loot
            state["xp"] = state.get("xp", 0) + room.get("xp_reward", 100)
            msg += (
                f"\n\n🏆 {boss['name']} DEFEATED!\n"
                f"✨ You gain {room['xp_reward']} XP!\n"
                f"💰 Loot collected: {', '.join(loot)}"
            )
    else:
        room["enemy_hp"] = max(0, room.get("enemy_hp", 30) - player_dmg)
        msg = (
            f"\n⚔ You strike for {player_dmg} damage! "
            f"[{room['enemy_hp']}/{room['enemy_max_hp']} HP]\n"
            f"💀 The creature retaliates — you take {enemy_dmg} damage!"
        )
        if room["enemy_hp"] <= 0:
            room["enemy_alive"] = False
            room["cleared"] = True
            loot = room.get("loot", [])
            state["inventory"] = state.get("inventory", []) + loot
            state["xp"] = state.get("xp", 0) + room.get("xp_reward", 20)
            msg += (
                f"\n\n✅ Room cleared!\n"
                f"✨ +{room['xp_reward']} XP  |  💰 Loot: {', '.join(loot)}"
            )

    # Apply damage to player
    state["hp"] = max(0, state.get("hp", 100) - enemy_dmg)

    return state, msg


def minimap_html(state: dict[str, Any]) -> str:
    """Return a tiny pixel minimap as HTML showing room progression."""
    rooms = state.get("rooms", [])
    idx   = state.get("room_index", 0)
    if not rooms:
        return ""

    boxes = []
    for i, room in enumerate(rooms):
        if i == idx:
            color, border = "#ffd36a", "2px solid #ffd36a"
            label = "▶"
        elif room.get("cleared"):
            color, border = "#8cff9b", "1px solid #8cff9b"
            label = "✓"
        elif room.get("is_boss"):
            color, border = "#ff6b6b", "1px dashed #ff6b6b"
            label = "☠"
        else:
            color, border = "#31513a", "1px solid #31513a"
            label = str(i + 1)

        tip = room.get("scene_name", f"Room {i+1}")
        boxes.append(
            f'<div title="{tip}" style="'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'width:32px;height:32px;border:{border};'
            f'color:{color};font-size:13px;font-family:monospace;'
            f'background:#0b1114;cursor:default;">{label}</div>'
        )

    connector = '<div style="display:inline-block;width:12px;height:1px;background:#31513a;vertical-align:middle;"></div>'
    inner = connector.join(boxes)
    return (
        f'<div style="padding:8px 10px;background:#0b1114;border:1px solid #31513a;'
        f'display:flex;align-items:center;gap:0;margin-bottom:4px;">'
        f'<span style="color:#4a9e4a;font-size:11px;letter-spacing:0.15em;margin-right:10px;">MAP</span>'
        f'{inner}</div>'
    )


def xp_bar_html(state: dict[str, Any]) -> str:
    xp       = state.get("xp", 0)
    level    = 1 + xp // 100
    xp_in_level = xp % 100
    return (
        f'<div style="border:1px solid #31513a;padding:6px 10px;background:#0b1114;margin-top:4px;">'
        f'<div style="color:#9cb9a3;font-size:11px;letter-spacing:0.1em;">LVL {level}  ·  XP {xp_in_level}/100</div>'
        f'<div style="background:#1a0808;margin-top:4px;border:1px solid #2a3a2a;">'
        f'<div style="height:6px;width:{xp_in_level}%;background:linear-gradient(90deg,#4a9e4a,#8cff9b);'
        f'transition:width 0.4s;"></div></div></div>'
    )