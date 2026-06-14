"""game_data.py — shared data for SnapQuest: classes, loot, helpers."""
from __future__ import annotations
import random

CHARACTER_CLASSES = ["Swordsman", "Archer", "Healer", "Rogue", "Mage"]

CLASS_DATA = {
    "Swordsman": {
        "icon": "⚔️", "tagline": "The Iron Vanguard",
        "desc": "Charges first, fears last. Built for face-to-face combat in tight dungeon corridors.",
        "stats": {"HP": 130, "ATK": 18, "DEF": 14, "SPD": 10},
        "perks": ["Shield Bash — stun enemy 1 turn", "Rallying Cry — +20 HP when below 30%", "Armor Expertise — DEF items give +50% bonus"],
        "playstyle": "Aggressive. Frontline. Walk up and hit hard.",
        "color": "#e8ffe8", "accent": "#4ade80",
    },
    "Archer": {
        "icon": "🏹", "tagline": "The Silent Wind",
        "desc": "Keeps distance. Every object in the room is a potential vantage point or obstacle.",
        "stats": {"HP": 100, "ATK": 22, "DEF": 8, "SPD": 18},
        "perks": ["Piercing Shot — ignores 50% of enemy DEF", "Eagle Eye — first strike each room always crits", "Quiver Master — ranged attacks never miss"],
        "playstyle": "Stay back. Strike first. Control the flow.",
        "color": "#fef9c3", "accent": "#facc15",
    },
    "Healer": {
        "icon": "💚", "tagline": "The Warden of Light",
        "desc": "Survives what others cannot. Turns the dungeon's own energy against it.",
        "stats": {"HP": 115, "ATK": 10, "DEF": 16, "SPD": 12},
        "perks": ["Mend — restore 25 HP per turn (passive)", "Holy Shield — 3-turn damage immunity, 1/room", "Life Tap — defeat enemy → gain 20 HP"],
        "playstyle": "Outlast. Heal. Endure. Win by attrition.",
        "color": "#dcfce7", "accent": "#86efac",
    },
    "Rogue": {
        "icon": "🗡️", "tagline": "The Shadow Knife",
        "desc": "Sees what others walk past. Strikes from angles the enemy never expected.",
        "stats": {"HP": 95, "ATK": 20, "DEF": 10, "SPD": 22},
        "perks": ["Backstab — first action each room deals 3× damage", "Vanish — 30% chance to dodge any attack", "Loot Sense — always finds one extra item per room"],
        "playstyle": "Strike fast. Dodge. Never fight fair.",
        "color": "#ede9fe", "accent": "#c084fc",
    },
    "Mage": {
        "icon": "🔮", "tagline": "The Arcane Eye",
        "desc": "Every object hums with power. Ordinary rooms are arcane batteries waiting to be drained.",
        "stats": {"HP": 90, "ATK": 28, "DEF": 6, "SPD": 14},
        "perks": ["Arcane Burst — 40% chance to deal double damage", "Object Reading — detect all hidden items on room entry", "Mana Shield — DEF scales with INT (ATK stat)"],
        "playstyle": "Glass cannon. High risk, highest reward.",
        "color": "#dbeafe", "accent": "#60a5fa",
    },
}

LOOT_TIERS = {
    "common":    {"color": "#9ca3af", "glow": "none",                          "label": "COMMON"},
    "uncommon":  {"color": "#4ade80", "glow": "0 0 8px rgba(74,222,128,0.5)",  "label": "UNCOMMON"},
    "rare":      {"color": "#60a5fa", "glow": "0 0 12px rgba(96,165,250,0.6)", "label": "RARE"},
    "epic":      {"color": "#c084fc", "glow": "0 0 16px rgba(192,132,252,0.7)","label": "EPIC"},
    "legendary": {"color": "#fbbf24", "glow": "0 0 24px rgba(251,191,36,0.8)", "label": "LEGENDARY"},
}

LOOT_TABLE = [
    {"name": "Rusty Dagger",      "tier": "common",    "type": "weapon",     "stat": "+3 ATK",                          "icon": "🗡️"},
    {"name": "Torn Cloak",        "tier": "common",    "type": "armor",      "stat": "+2 DEF",                          "icon": "🧥"},
    {"name": "Stale Bread",       "tier": "common",    "type": "consumable", "stat": "+10 HP",                          "icon": "🍞"},
    {"name": "Copper Coin",       "tier": "common",    "type": "misc",       "stat": "+5 Gold",                         "icon": "🪙"},
    {"name": "Pebble Shard",      "tier": "common",    "type": "misc",       "stat": "+1 ATK",                          "icon": "🪨"},
    {"name": "Healing Herbs",     "tier": "uncommon",  "type": "consumable", "stat": "+30 HP",                          "icon": "🌿"},
    {"name": "Iron Shield",       "tier": "uncommon",  "type": "armor",      "stat": "+8 DEF",                          "icon": "🛡️"},
    {"name": "Shadow Cloak",      "tier": "uncommon",  "type": "armor",      "stat": "+5 DEF, +EVD",                    "icon": "🌑"},
    {"name": "Throwing Stars",    "tier": "uncommon",  "type": "weapon",     "stat": "+6 ATK",                          "icon": "⭐"},
    {"name": "Smoke Bomb",        "tier": "uncommon",  "type": "consumable", "stat": "Stun enemy",                      "icon": "💨"},
    {"name": "Lockpick Set",      "tier": "uncommon",  "type": "tool",       "stat": "Open locks",                      "icon": "🔑"},
    {"name": "Enchanted Rope",    "tier": "rare",      "type": "tool",       "stat": "Escape trap",                     "icon": "🪢"},
    {"name": "Arcane Scroll",     "tier": "rare",      "type": "consumable", "stat": "+50 HP + 25 DMG",                 "icon": "📜"},
    {"name": "Rune Stone",        "tier": "rare",      "type": "misc",       "stat": "+15 ATK (3 turns)",               "icon": "🔮"},
    {"name": "Bone Dagger",       "tier": "rare",      "type": "weapon",     "stat": "+12 ATK, lifesteal",              "icon": "🦴"},
    {"name": "Ember Flask",       "tier": "rare",      "type": "consumable", "stat": "Burn enemy (3 turns)",            "icon": "🔥"},
    {"name": "Silver Sigil Ring", "tier": "rare",      "type": "armor",      "stat": "+10 DEF, magic resist",           "icon": "💍"},
    {"name": "Thornwood Staff",   "tier": "epic",      "type": "weapon",     "stat": "+20 ATK, AOE",                    "icon": "🪄"},
    {"name": "Crystal Prism",     "tier": "epic",      "type": "misc",       "stat": "Reveal hidden paths",             "icon": "💎"},
    {"name": "Void Dagger",       "tier": "epic",      "type": "weapon",     "stat": "+18 ATK, ignore DEF",             "icon": "🌀"},
    {"name": "Phantom Mantle",    "tier": "epic",      "type": "armor",      "stat": "+15 DEF, 20% dodge",              "icon": "👻"},
    {"name": "Blood Vial",        "tier": "epic",      "type": "consumable", "stat": "Full HP restore",                 "icon": "🩸"},
    {"name": "Orb of Zot",        "tier": "legendary", "type": "misc",       "stat": "+50 ATK, reveal boss weakness",   "icon": "🌐"},
    {"name": "Wraithblade",       "tier": "legendary", "type": "weapon",     "stat": "+35 ATK, drain soul",             "icon": "⚔️"},
    {"name": "Dragonscale Armor", "tier": "legendary", "type": "armor",      "stat": "+30 DEF, fire immunity",          "icon": "🐉"},
    {"name": "Eternal Lantern",   "tier": "legendary", "type": "misc",       "stat": "Never lose HP to traps",          "icon": "🏮"},
]

_TIER_WEIGHTS = {"common": 45, "uncommon": 28, "rare": 16, "epic": 8, "legendary": 3}


def roll_loot(n: int = 2) -> list[dict]:
    """Roll n loot items with weighted tier probability."""
    pool_by_tier: dict[str, list[dict]] = {}
    for item in LOOT_TABLE:
        pool_by_tier.setdefault(item["tier"], []).append(item)
    tiers = list(_TIER_WEIGHTS.keys())
    weights = list(_TIER_WEIGHTS.values())
    result = []
    for _ in range(n):
        tier = random.choices(tiers, weights=weights, k=1)[0]
        result.append(random.choice(pool_by_tier[tier]))
    return result