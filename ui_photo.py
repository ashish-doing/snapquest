"""ui_photo.py — SnapQuest v4 — Full Game UI.

Three screens rendered entirely in gr.HTML + gr.State:
  SCREEN 1 — Landing / Photo Upload (drag & drop, object preview)
  SCREEN 2 — Class Selection (cards with stats, perks, playstyle)  
  SCREEN 3 — Dungeon Combat (full game HUD, scene, inventory, loot)

Gradio components are hidden behind the custom HTML layer.
JS <-> Python bridge via hidden gr.Textbox + gr.Button triggers.
"""
from __future__ import annotations
import html as _h
import json
import gradio as gr

from engine_photo import start_photo_game, take_photo_action
from dungeon import current_room, can_advance, minimap_html, xp_bar_html
from voice import clean_for_speech, speak, transcribe_audio

CHARACTER_CLASSES = ["Swordsman", "Archer", "Healer", "Rogue", "Mage"]

# ════════════════════════════════════════════════════════════════════════════
# LOOT SYSTEM
# ════════════════════════════════════════════════════════════════════════════

LOOT_TIERS = {
    "common":    {"color": "#9ca3af", "glow": "none",                        "label": "COMMON"},
    "uncommon":  {"color": "#4ade80", "glow": "0 0 8px rgba(74,222,128,0.5)","label": "UNCOMMON"},
    "rare":      {"color": "#60a5fa", "glow": "0 0 12px rgba(96,165,250,0.6)","label": "RARE"},
    "epic":      {"color": "#c084fc", "glow": "0 0 16px rgba(192,132,252,0.7)","label": "EPIC"},
    "legendary": {"color": "#fbbf24", "glow": "0 0 24px rgba(251,191,36,0.8)","label": "LEGENDARY"},
}

LOOT_TABLE = [
    # common
    {"name": "Rusty Dagger",       "tier": "common",    "type": "weapon", "stat": "+3 ATK",  "icon": "🗡️"},
    {"name": "Torn Cloak",         "tier": "common",    "type": "armor",  "stat": "+2 DEF",  "icon": "🧥"},
    {"name": "Stale Bread",        "tier": "common",    "type": "consumable","stat": "+10 HP","icon": "🍞"},
    {"name": "Copper Coin",        "tier": "common",    "type": "misc",   "stat": "+5 Gold", "icon": "🪙"},
    {"name": "Pebble Shard",       "tier": "common",    "type": "misc",   "stat": "+1 ATK",  "icon": "🪨"},
    # uncommon
    {"name": "Healing Herbs",      "tier": "uncommon",  "type": "consumable","stat": "+30 HP","icon": "🌿"},
    {"name": "Iron Shield",        "tier": "uncommon",  "type": "armor",  "stat": "+8 DEF",  "icon": "🛡️"},
    {"name": "Shadow Cloak",       "tier": "uncommon",  "type": "armor",  "stat": "+5 DEF, +EVD","icon": "🌑"},
    {"name": "Throwing Stars",     "tier": "uncommon",  "type": "weapon", "stat": "+6 ATK",  "icon": "⭐"},
    {"name": "Smoke Bomb",         "tier": "uncommon",  "type": "consumable","stat": "Stun enemy","icon": "💨"},
    {"name": "Lockpick Set",       "tier": "uncommon",  "type": "tool",   "stat": "Open locks","icon": "🔑"},
    # rare
    {"name": "Enchanted Rope",     "tier": "rare",      "type": "tool",   "stat": "Escape trap","icon": "🪢"},
    {"name": "Arcane Scroll",      "tier": "rare",      "type": "consumable","stat": "+50 HP + deals 25 DMG","icon": "📜"},
    {"name": "Rune Stone",         "tier": "rare",      "type": "misc",   "stat": "+15 ATK for 3 turns","icon": "🔮"},
    {"name": "Bone Dagger",        "tier": "rare",      "type": "weapon", "stat": "+12 ATK, lifesteal","icon": "🦴"},
    {"name": "Ember Flask",        "tier": "rare",      "type": "consumable","stat": "Burns enemy 3 turns","icon": "🔥"},
    {"name": "Silver Sigil Ring",  "tier": "rare",      "type": "armor",  "stat": "+10 DEF, magic resist","icon": "💍"},
    # epic
    {"name": "Thornwood Staff",    "tier": "epic",      "type": "weapon", "stat": "+20 ATK, AOE","icon": "🪄"},
    {"name": "Crystal Prism",      "tier": "epic",      "type": "misc",   "stat": "Reveal hidden paths","icon": "💎"},
    {"name": "Void Dagger",        "tier": "epic",      "type": "weapon", "stat": "+18 ATK, ignore DEF","icon": "🌀"},
    {"name": "Phantom Mantle",     "tier": "epic",      "type": "armor",  "stat": "+15 DEF, 20% dodge","icon": "👻"},
    {"name": "Blood Vial",         "tier": "epic",      "type": "consumable","stat": "Full HP restore","icon": "🩸"},
    # legendary
    {"name": "Orb of Zot",         "tier": "legendary", "type": "misc",   "stat": "+50 ATK, reveals boss weakness","icon": "🌐"},
    {"name": "Wraithblade",        "tier": "legendary", "type": "weapon", "stat": "+35 ATK, drain soul","icon": "⚔️"},
    {"name": "Dragonscale Armor",  "tier": "legendary", "type": "armor",  "stat": "+30 DEF, fire immunity","icon": "🐉"},
    {"name": "Eternal Lantern",    "tier": "legendary", "type": "misc",   "stat": "Never lose HP from traps","icon": "🏮"},
]

import random

def _roll_loot(n: int = 3) -> list[dict]:
    """Roll n loot items with weighted tier probability."""
    weights = {"common": 45, "uncommon": 28, "rare": 16, "epic": 8, "legendary": 3}
    pool_by_tier = {}
    for item in LOOT_TABLE:
        pool_by_tier.setdefault(item["tier"], []).append(item)
    result = []
    tiers = list(weights.keys())
    tier_weights = list(weights.values())
    for _ in range(n):
        tier = random.choices(tiers, weights=tier_weights, k=1)[0]
        item = random.choice(pool_by_tier[tier])
        result.append(item)
    return result

# ════════════════════════════════════════════════════════════════════════════
# CLASS DATA
# ════════════════════════════════════════════════════════════════════════════

CLASS_DATA = {
    "Swordsman": {
        "icon": "⚔️",
        "tagline": "The Iron Vanguard",
        "desc": "Charges first, fears last. Built for face-to-face combat in tight dungeon corridors.",
        "stats": {"HP": 130, "ATK": 18, "DEF": 14, "SPD": 10},
        "perks": ["Shield Bash — stun enemy 1 turn", "Rallying Cry — +20 HP when below 30%", "Armor Expertise — DEF items give +50% bonus"],
        "playstyle": "Aggressive. Frontline. Walk up and hit hard.",
        "color": "#e8ffe8",
        "accent": "#4ade80",
        "art": ["  ███  ","  ███  "," ██╬██ ","  ╫╫╫  ","  ╫ ╫  "," ╫   ╫ "],
    },
    "Archer": {
        "icon": "🏹",
        "tagline": "The Silent Wind",
        "desc": "Keeps distance. Every object in the room is a potential vantage point or obstacle.",
        "stats": {"HP": 100, "ATK": 22, "DEF": 8, "SPD": 18},
        "perks": ["Piercing Shot — ignores 50% of enemy DEF", "Eagle Eye — first strike each room always crits", "Quiver Master — ranged attacks never miss"],
        "playstyle": "Stay back. Strike first. Control the flow.",
        "color": "#fef9c3",
        "accent": "#facc15",
        "art": ["  ███  ","  ███  ","──█▶── ","  ███  ","  █ █  "," █   █ "],
    },
    "Healer": {
        "icon": "💚",
        "tagline": "The Warden of Light",
        "desc": "Survives what others cannot. Turns the dungeon's own energy against it.",
        "stats": {"HP": 115, "ATK": 10, "DEF": 16, "SPD": 12},
        "perks": ["Mend — restore 25 HP per turn (passive)", "Holy Shield — 3-turn damage immunity, 1/room", "Life Tap — defeat enemy → gain 20 HP"],
        "playstyle": "Outlast. Heal. Endure. Win by attrition.",
        "color": "#dcfce7",
        "accent": "#86efac",
        "art": ["  ███  ","  ███  "," ██+██ ","  ╫+╫  ","  ╫ ╫  "," ╫   ╫ "],
    },
    "Rogue": {
        "icon": "🗡️",
        "tagline": "The Shadow Knife",
        "desc": "Sees what others walk past. Strikes from angles the enemy never expected.",
        "stats": {"HP": 95, "ATK": 20, "DEF": 10, "SPD": 22},
        "perks": ["Backstab — first action each room deals 3× damage", "Vanish — 30% chance to dodge any attack", "Loot Sense — always finds one extra item per room"],
        "playstyle": "Strike fast. Dodge. Never fight fair.",
        "color": "#ede9fe",
        "accent": "#c084fc",
        "art": ["  ███  ","  ███  ","  ███▶ ","  ╫╫╫  ","  ╫ ╫  ","╫╫   ╫ "],
    },
    "Mage": {
        "icon": "🔮",
        "tagline": "The Arcane Eye",
        "desc": "Every object hums with power. Ordinary rooms are arcane batteries waiting to be drained.",
        "stats": {"HP": 90, "ATK": 28, "DEF": 6, "SPD": 14},
        "perks": ["Arcane Burst — 40% chance to deal double damage", "Object Reading — detect all hidden items on room entry", "Mana Shield — DEF scales with INT (ATK stat)"],
        "playstyle": "Glass cannon. High risk, highest reward.",
        "color": "#dbeafe",
        "accent": "#60a5fa",
        "art": ["  ███  ","  ███  ","*█╬█╬*","  ╫╫╫  ","  ╫ ╫  ","* ╫ ╫*"],
    },
}

# ════════════════════════════════════════════════════════════════════════════
# GAME STATE HELPERS
# ════════════════════════════════════════════════════════════════════════════

def _safe_state(state):
    return state if isinstance(state, dict) else {}

def _cur_room(state):
    rooms = state.get("rooms", [])
    idx = state.get("room_index", 0)
    if not rooms: return {}
    return rooms[min(idx, len(rooms)-1)]

def _inv_html(state) -> str:
    inv = state.get("inventory", [])
    if not inv: return '<div style="color:#4a5568;font-size:12px;">Empty</div>'
    rows = ""
    for item in inv:
        if isinstance(item, dict):
            td = LOOT_TIERS.get(item.get("tier","common"), LOOT_TIERS["common"])
            rows += (
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
                f'border-bottom:1px solid #1a2a1a;">'
                f'<span style="font-size:16px;">{item.get("icon","📦")}</span>'
                f'<div><div style="color:{td["color"]};font-size:11px;'
                f'text-shadow:{td["glow"]};font-weight:bold;">{_h.escape(item.get("name","?"))}</div>'
                f'<div style="color:#4a6a4a;font-size:10px;">{_h.escape(item.get("stat",""))}</div></div>'
                f'<div style="margin-left:auto;font-size:9px;color:{td["color"]};'
                f'opacity:0.7;">{td["label"]}</div>'
                f'</div>'
            )
        else:
            rows += f'<div style="color:#9ca3af;font-size:12px;padding:3px 0;">• {_h.escape(str(item))}</div>'
    return rows

def _loot_popup_html(items: list[dict]) -> str:
    if not items: return ""
    cards = ""
    for item in items:
        td = LOOT_TIERS.get(item.get("tier","common"), LOOT_TIERS["common"])
        cards += (
            f'<div style="border:1px solid {td["color"]};background:#080f08;'
            f'padding:12px 16px;min-width:140px;text-align:center;'
            f'box-shadow:{td["glow"]};">'
            f'<div style="font-size:28px;margin-bottom:6px;">{item.get("icon","📦")}</div>'
            f'<div style="color:{td["color"]};font-size:10px;letter-spacing:2px;margin-bottom:4px;">'
            f'{td["label"]}</div>'
            f'<div style="color:#d4eedd;font-size:13px;font-weight:bold;margin-bottom:4px;">'
            f'{_h.escape(item.get("name","?"))}</div>'
            f'<div style="color:#6b9a75;font-size:11px;">{_h.escape(item.get("stat",""))}</div>'
            f'</div>'
        )
    return (
        f'<div id="loot-popup" style="'
        f'position:fixed;inset:0;background:rgba(0,0,0,0.85);z-index:9999;'
        f'display:flex;flex-direction:column;align-items:center;justify-content:center;'
        f'font-family:Courier New,monospace;">'
        f'<div style="color:#fbbf24;font-size:22px;letter-spacing:6px;margin-bottom:24px;'
        f'text-shadow:0 0 20px rgba(251,191,36,0.8);">✦ LOOT FOUND ✦</div>'
        f'<div style="display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin-bottom:28px;">'
        f'{cards}</div>'
        f'<button onclick="document.getElementById(\'loot-popup\').remove()" '
        f'style="background:#0a1a0a;border:1px solid #4ade80;color:#4ade80;'
        f'font-family:Courier New,monospace;font-size:14px;letter-spacing:4px;'
        f'padding:12px 32px;cursor:pointer;">COLLECT ALL</button>'
        f'</div>'
    )

# ════════════════════════════════════════════════════════════════════════════
# SCREEN HTML BUILDERS
# ════════════════════════════════════════════════════════════════════════════

def _screen1_html(photo_data: list[dict]) -> str:
    """Landing + photo upload screen."""
    slots = ""
    for i in range(3):
        d = photo_data[i] if i < len(photo_data) else {}
        has = bool(d.get("path"))
        label = ["ENTRY HALL","INNER CHAMBER","BOSS LAIR"][i]
        num = ["01","02","03"][i]
        opt = "" if i == 0 else " (optional)"
        objs = d.get("objects", [])
        obj_html = ""
        if objs:
            obj_html = "".join(
                f'<span style="border:1px solid #2a4a2a;padding:2px 8px;'
                f'font-size:10px;color:#4ade80;margin:2px;display:inline-block;">'
                f'{_h.escape(o)}</span>' for o in objs
            )
        boss_label = ""
        if i == 2 and objs:
            boss_label = (
                f'<div style="margin-top:8px;border:1px solid #ff5555;padding:6px 10px;'
                f'background:#0f0303;color:#ff5555;font-size:11px;letter-spacing:2px;">'
                f'☠ BOSS: {_h.escape(objs[0].upper())} GUARDIAN</div>'
            )
        slot_inner = ""
        if has:
            slot_inner = (
                f'<div style="color:#4ade80;font-size:11px;letter-spacing:2px;margin-bottom:8px;">'
                f'✓ PHOTO LOADED</div>'
                f'<div style="margin-bottom:8px;flex-wrap:wrap;">{obj_html}</div>'
                f'{boss_label}'
            )
        else:
            slot_inner = (
                f'<div style="color:#1e3d28;font-size:32px;margin-bottom:8px;">+</div>'
                f'<div style="color:#2a5a38;font-size:11px;letter-spacing:2px;">UPLOAD {label}</div>'
                f'<div style="color:#1a3020;font-size:10px;margin-top:4px;">{opt}</div>'
            )
        slots += (
            f'<div style="border:1px solid {"#2a5a38" if has else "#1a2a1a"};'
            f'background:{"#040d06" if has else "#030806"};'
            f'padding:16px;min-height:100px;display:flex;flex-direction:column;'
            f'align-items:{"flex-start" if has else "center"};'
            f'justify-content:{"flex-start" if has else "center"};'
            f'box-shadow:{"0 0 20px rgba(74,222,128,0.06)" if has else "none"};">'
            f'<div style="color:#2a5a38;font-size:10px;letter-spacing:3px;margin-bottom:8px;">'
            f'ROOM {num} · {label}</div>'
            f'{slot_inner}'
            f'</div>'
        )
    n_loaded = sum(1 for d in photo_data if d.get("path"))
    can_proceed = n_loaded >= 1
    btn_style = (
        'background:linear-gradient(90deg,#0a2a10,#0f3818);border:1px solid #4ade80;'
        'color:#4ade80;font-family:Courier New,monospace;font-size:14px;letter-spacing:5px;'
        'padding:16px 0;width:100%;cursor:pointer;'
        'box-shadow:0 0 24px rgba(74,222,128,0.15);text-transform:uppercase;'
    ) if can_proceed else (
        'background:#050a06;border:1px solid #1a2a1a;color:#2a4a2a;'
        'font-family:Courier New,monospace;font-size:14px;letter-spacing:5px;'
        'padding:16px 0;width:100%;cursor:not-allowed;text-transform:uppercase;'
    )
    n_label = {1:"1 room",2:"2 rooms",3:"3-room dungeon"}.get(n_loaded,"0 rooms")
    return f"""
<div style="font-family:'Courier New',monospace;min-height:100vh;background:#03060a;
  display:flex;flex-direction:column;align-items:center;justify-content:flex-start;
  padding:0 0 40px;">

  <!-- HERO -->
  <div style="width:100%;background:linear-gradient(180deg,#040e07 0%,#03060a 100%);
    border-bottom:1px solid #1a2a1a;padding:40px 20px 32px;text-align:center;
    position:relative;overflow:hidden;">
    <div style="position:absolute;inset:0;background:
      repeating-linear-gradient(0deg,transparent,transparent 3px,
      rgba(74,222,128,0.012) 3px,rgba(74,222,128,0.012) 4px);pointer-events:none;"></div>
    <div style="position:relative;">
      <div style="color:#4ade80;font-size:42px;font-weight:900;letter-spacing:12px;
        text-shadow:0 0 20px rgba(74,222,128,0.9),0 0 60px rgba(74,222,128,0.4);
        margin-bottom:6px;">S N A P Q U E S T</div>
      <div style="color:#1a5a28;font-size:12px;letter-spacing:6px;margin-bottom:24px;">
        YOUR ROOM · YOUR DUNGEON · MINICPM-V 4.6</div>
      <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:28px;">
        <span style="border:1px solid #1e3d28;padding:4px 12px;font-size:10px;
          color:#2a5a38;letter-spacing:2px;">1.3B PARAMS</span>
        <span style="border:1px solid #1e3d28;padding:4px 12px;font-size:10px;
          color:#2a5a38;letter-spacing:2px;">MODAL A10G GPU</span>
        <span style="border:1px solid #1e3d28;padding:4px 12px;font-size:10px;
          color:#2a5a38;letter-spacing:2px;">MULTI-ROOM DUNGEON</span>
        <span style="border:1px solid #5a1a1a;padding:4px 12px;font-size:10px;
          color:#aa3333;letter-spacing:2px;">☠ BOSS FIGHTS</span>
      </div>
      <div style="max-width:540px;margin:0 auto;color:#2a5a38;font-size:13px;line-height:1.8;">
        Upload photos of any real space.<br>
        MiniCPM-V reads every object inside them.<br>
        Your <span style="color:#4ade80;">bookshelf</span> becomes the Archive of Tomes.
        Your <span style="color:#ff5555;">lamp becomes the boss.</span>
      </div>
    </div>
  </div>

  <!-- UPLOAD AREA -->
  <div style="width:100%;max-width:760px;padding:32px 20px 0;">
    <div style="color:#2a5a38;font-size:10px;letter-spacing:4px;margin-bottom:16px;">
      ▸ UPLOAD PHOTOS ( 1 MINIMUM · 3 FOR FULL DUNGEON )
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
      {slots}
    </div>

    <!-- HOW IT WORKS -->
    <div style="border:1px solid #1a2a1a;background:#040d06;padding:16px 20px;
      margin-bottom:20px;">
      <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:12px;">
        HOW IT WORKS
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
        <div style="text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">📸</div>
          <div style="color:#2a5a38;font-size:11px;line-height:1.6;">
            AI reads every object in your photo
          </div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">🏰</div>
          <div style="color:#2a5a38;font-size:11px;line-height:1.6;">
            Objects become dungeon elements &amp; monsters
          </div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">☠</div>
          <div style="color:#aa3333;font-size:11px;line-height:1.6;">
            Last photo's main object is your final boss
          </div>
        </div>
      </div>
    </div>

    <div style="color:#1e3d28;font-size:10px;letter-spacing:2px;margin-bottom:10px;text-align:right;">
      {n_label} ready
    </div>

    <button {"" if not can_proceed else 'onclick="window.__sq_proceed_to_class()"'} 
      style="{btn_style}">
      {"UPLOAD A PHOTO TO CONTINUE" if not can_proceed else "▶  CHOOSE YOUR CLASS  →"}
    </button>
  </div>
</div>"""

def _screen2_html(selected_class: str) -> str:
    """Class selection screen."""
    cards = ""
    for cls, d in CLASS_DATA.items():
        is_sel = cls == selected_class
        border = "2px solid " + d["accent"] if is_sel else "1px solid #1a2a1a"
        bg = "#040d06" if is_sel else "#030806"
        shadow = "0 0 30px " + d["accent"] + "33" if is_sel else "none"
        stats_html = "".join(
            f'<div style="text-align:center;"><div style="color:{d["accent"]};font-size:16px;font-weight:bold;">{v}</div><div style="color:#2a4a2a;font-size:9px;letter-spacing:1px;">{k}</div></div>'
            for k, v in d["stats"].items()
        )
        perks_html = "".join(
            f'<div style="color:#4a6a4a;font-size:11px;padding:4px 0;border-bottom:1px solid #1a2a1a;">▸ {_h.escape(p)}</div>'
            for p in d["perks"]
        )
        art_html = "".join(
            f'<div style="color:{d["accent"]};text-shadow:0 0 8px {d["accent"]};">{_h.escape(row)}</div>'
            for row in d["art"]
        )
        sel_badge = f'<div style="text-align:center;color:{d["accent"]};font-size:11px;letter-spacing:3px;margin-top:10px;">✓ SELECTED</div>' if is_sel else ""
        cards += (
            f'<div onclick="window.__sq_select_class(\'{cls}\')" '
            f'style="border:{border};background:{bg};'
            f'padding:20px 16px;cursor:pointer;transition:all 0.2s;'
            f'box-shadow:{shadow};">'
            f'<div style="text-align:center;margin-bottom:14px;">'
            f'<div style="font-family:Courier New,monospace;font-size:13px;line-height:1.4;margin-bottom:8px;">{art_html}</div>'
            f'<div style="font-size:20px;">{d["icon"]}</div>'
            f'<div style="color:{d["color"]};font-size:14px;font-weight:bold;letter-spacing:3px;margin-top:6px;">{cls.upper()}</div>'
            f'<div style="color:{d["accent"]};font-size:10px;letter-spacing:1px;margin-top:2px;opacity:0.8;">{_h.escape(d["tagline"])}</div>'
            f'</div>'
            f'<div style="color:#4a6a4a;font-size:11px;line-height:1.6;margin-bottom:12px;border-top:1px solid #1a2a1a;padding-top:10px;">{_h.escape(d["desc"])}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:4px;margin-bottom:12px;background:#020705;padding:10px 4px;">{stats_html}</div>'
            f'<div style="margin-bottom:10px;">{perks_html}</div>'
            f'<div style="border:1px solid #1a2a1a;padding:6px 8px;color:#2a4a2a;font-size:10px;letter-spacing:1px;font-style:italic;">"{_h.escape(d["playstyle"])}"</div>'
            f'{sel_badge}'
            f'</div>'
        )
    can_start = bool(selected_class)
    if can_start:
        btn_s = (
            'background:linear-gradient(90deg,#0a1a24,#0f2a3a);border:1px solid #60a5fa;'
            'color:#60a5fa;font-family:Courier New,monospace;font-size:14px;letter-spacing:5px;'
            'padding:16px 0;width:100%;cursor:pointer;box-shadow:0 0 24px rgba(96,165,250,0.15);'
        )
        btn_label = "▶  ENTER THE DUNGEON  →"
        btn_onclick = 'onclick="window.__sq_start_dungeon()"'
    else:
        btn_s = (
            'background:#050a06;border:1px solid #1a2a1a;color:#2a4a2a;'
            'font-family:Courier New,monospace;font-size:14px;letter-spacing:5px;'
            'padding:16px 0;width:100%;cursor:not-allowed;'
        )
        btn_label = "SELECT A CLASS FIRST"
        btn_onclick = ""
    return f"""
<div style="font-family:'Courier New',monospace;min-height:100vh;background:#03060a;padding:0 0 40px;">
  <div style="border-bottom:1px solid #1a2a1a;background:#040d06;padding:16px 24px;display:flex;align-items:center;justify-content:space-between;">
    <span style="color:#4ade80;font-size:20px;font-weight:900;letter-spacing:6px;text-shadow:0 0 16px rgba(74,222,128,0.7);">⚔ SNAPQUEST</span>
    <button onclick="window.__sq_go_back()" style="background:none;border:1px solid #1a2a1a;color:#2a5a38;font-family:Courier New,monospace;font-size:11px;letter-spacing:2px;padding:6px 14px;cursor:pointer;">← BACK</button>
  </div>
  <div style="max-width:1100px;margin:0 auto;padding:28px 20px 0;">
    <div style="text-align:center;margin-bottom:28px;">
      <div style="color:#4ade80;font-size:18px;letter-spacing:6px;margin-bottom:4px;">CHOOSE YOUR CLASS</div>
      <div style="color:#1e3d28;font-size:11px;letter-spacing:3px;">YOUR LENS CHANGES HOW THE DUNGEON REVEALS ITSELF</div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:28px;">{cards}</div>
    <button {btn_onclick} style="{btn_s}">{btn_label}</button>
  </div>
</div>"""


def _screen3_html(state: dict, story: str, parsed: dict | None, loot_items: list | None) -> str:
    """Main dungeon game screen."""
    s = _safe_state(state)
    room = _cur_room(s)
    rooms = s.get("rooms", [])
    idx = s.get("room_index", 0)
    total_rooms = len(rooms)
    cls = s.get("character_class", "Swordsman")
    cd = CLASS_DATA.get(cls, CLASS_DATA["Swordsman"])
    hp = int(s.get("hp", 100))
    max_hp = int(s.get("max_hp", 100))
    xp = int(s.get("xp", 0))
    level = 1 + xp // 100
    hp_pct = max(0, min(100, int(hp / max(max_hp, 1) * 100)))
    hp_color = "#ff5555" if hp_pct < 30 else "#facc15" if hp_pct < 60 else "#4ade80"
    is_boss = room.get("is_boss", False)
    boss = room.get("boss") if is_boss else None
    boss_alive = boss.get("alive", True) if boss else False
    choices = s.get("current_choices", ["Look around", "Move forward", "Hold position"])
    scene_name = room.get("scene_name", "Unknown Realm")
    objects = room.get("objects_found", [])
    diff = room.get("difficulty", "easy").upper()
    diff_color = {"EASY": "#4ade80", "MEDIUM": "#facc15", "HARD": "#ff5555"}.get(diff, "#4ade80")
    # Minimap
    map_slots = ""
    for i, r in enumerate(rooms):
        if i == idx:
            c, sym, bc = "#facc15", "▶", "2px solid #facc15"
        elif r.get("cleared"):
            c, sym, bc = "#4ade80", "✓", "1px solid #4ade80"
        elif r.get("is_boss"):
            c, sym, bc = "#ff5555", "☠", "1px dashed #ff5555"
        else:
            c, sym, bc = "#1e3d28", str(i+1), "1px solid #1e3d28"
        map_slots += (
            f'<div style="width:28px;height:28px;border:{bc};color:{c};'
            f'display:flex;align-items:center;justify-content:center;font-size:12px;'
            f'background:#030806;">{sym}</div>'
        )
        if i < len(rooms)-1:
            map_slots += '<div style="width:14px;height:1px;background:#1a2a1a;align-self:center;"></div>'
    # Story lines
    story_lines = ""
    for line in (story or "").split("\n"):
        if line.startswith("═") or line.startswith("─"):
            story_lines += f'<div style="color:#1e3d28;margin:6px 0;">{_h.escape(line)}</div>'
        elif line.startswith("▷") or line.startswith(">"):
            story_lines += f'<div style="color:#60a5fa;margin-top:8px;">{_h.escape(line)}</div>'
        elif line.startswith("⚔") or line.startswith("💀"):
            story_lines += f'<div style="color:#ff5555;font-weight:bold;">{_h.escape(line)}</div>'
        elif line.startswith("✅") or line.startswith("🏆"):
            story_lines += f'<div style="color:#4ade80;font-weight:bold;">{_h.escape(line)}</div>'
        elif line.startswith("💰") or line.startswith("✨"):
            story_lines += f'<div style="color:#fbbf24;">{_h.escape(line)}</div>'
        elif line.strip():
            story_lines += f'<div style="color:#a0c4a8;line-height:1.7;">{_h.escape(line)}</div>'
        else:
            story_lines += '<div style="height:6px;"></div>'
    # Choice buttons
    choice_btns = ""
    for i, c in enumerate(choices[:3]):
        if is_boss and boss_alive:
            btn_style = (
                'background:#0f0303;border:1px solid #5a1a1a;color:#ff8888;'
                'font-family:Courier New,monospace;font-size:12px;padding:12px 10px;'
                'cursor:pointer;width:100%;text-align:left;letter-spacing:0.5px;'
                'transition:all 0.18s;line-height:1.4;'
            )
        else:
            btn_style = (
                'background:#040d06;border:1px solid #1a3a1a;color:#a0c4a8;'
                'font-family:Courier New,monospace;font-size:12px;padding:12px 10px;'
                'cursor:pointer;width:100%;text-align:left;letter-spacing:0.5px;'
                'transition:all 0.18s;line-height:1.4;'
            )
        num = ["①","②","③"][i]
        choice_btns += (
            f'<button onclick="window.__sq_do_action({json.dumps(c)})" '
            f'style="{btn_style}" '
            f'onmouseover="this.style.borderColor=\'{"#ff5555" if is_boss else "#4ade80"}\';'
            f'this.style.color=\'{"#ff8888" if is_boss else "#4ade80"}\';" '
            f'onmouseout="this.style.borderColor=\'{"#5a1a1a" if is_boss else "#1a3a1a"}\';'
            f'this.style.color=\'{"#ff8888" if is_boss else "#a0c4a8"}\';">'
            f'<span style="opacity:0.5;margin-right:8px;">{num}</span>{_h.escape(c)}'
            f'</button>'
        )
    # Objects as "monsters"
    monster_html = ""
    for obj in objects:
        if is_boss and obj == objects[0] and boss:
            monster_html += (
                f'<div style="border:1px solid #ff5555;background:#0a0202;'
                f'padding:6px 12px;font-size:11px;color:#ff5555;'
                f'box-shadow:0 0 12px rgba(255,85,85,0.2);">☠ {_h.escape(obj.upper())}</div>'
            )
        else:
            monster_html += (
                f'<div style="border:1px solid #1a3a1a;background:#030806;'
                f'padding:4px 10px;font-size:11px;color:#4a6a4a;">◆ {_h.escape(obj)}</div>'
            )
    # Loot popup
    loot_html = _loot_popup_html(loot_items) if loot_items else ""
    # Boss panel
    boss_panel = ""
    if is_boss and boss:
        b_hp = boss.get("hp", 0)
        b_max = boss.get("max_hp", 100)
        b_pct = max(0, min(100, int(b_hp / max(b_max, 1) * 100)))
        b_name = _h.escape(boss.get("name", "Unknown"))
        if boss_alive:
            boss_panel = (
                f'<div style="border:2px solid #ff5555;background:#0a0202;'
                f'padding:12px 16px;margin-bottom:12px;'
                f'animation:bossGlow 2s infinite alternate;">'
                f'<div style="color:#ff5555;font-size:10px;letter-spacing:4px;'
                f'margin-bottom:4px;">☠  BOSS ENCOUNTER</div>'
                f'<div style="color:#ff8888;font-size:16px;font-weight:bold;'
                f'margin-bottom:8px;">{b_name}</div>'
                f'<div style="height:8px;background:#1a0404;border:1px solid #3a1010;'
                f'margin-bottom:4px;overflow:hidden;">'
                f'<div style="height:100%;width:{b_pct}%;'
                f'background:linear-gradient(90deg,#7f0000,#ff5555);'
                f'transition:width 0.4s;"></div></div>'
                f'<div style="color:#ff5555;font-size:11px;">{b_hp} / {b_max} HP</div>'
                f'</div>'
            )
        else:
            boss_panel = (
                f'<div style="border:1px solid #4ade80;background:#030e05;'
                f'padding:10px 16px;margin-bottom:12px;text-align:center;'
                f'color:#4ade80;font-size:13px;letter-spacing:3px;">'
                f'✅ {b_name} DEFEATED</div>'
            )
    advance_btn = ""
    if can_advance(s):
        advance_btn = (
            '<button onclick="window.__sq_do_action(\'go deeper\')" '
            'style="width:100%;background:linear-gradient(90deg,#0a2a10,#0f3818);'
            'border:1px solid #4ade80;color:#4ade80;font-family:Courier New,monospace;'
            'font-size:13px;letter-spacing:4px;padding:12px;cursor:pointer;margin-bottom:12px;'
            'box-shadow:0 0 16px rgba(74,222,128,0.2);">▶  GO DEEPER  →</button>'
        )
    inv_html = _inv_html(s)
    return f"""
{loot_html}
<style>
@keyframes bossGlow {{
  from {{ box-shadow: 0 0 16px rgba(255,85,85,0.25); }}
  to   {{ box-shadow: 0 0 40px rgba(255,85,85,0.6); }}
}}
@keyframes scanline {{
  0%   {{ background-position: 0 0; }}
  100% {{ background-position: 0 4px; }}
}}
</style>
<div id="sq-game" style="font-family:'Courier New',monospace;background:#03060a;
  min-height:100vh;display:flex;flex-direction:column;">

  <!-- TOP HUD -->
  <div style="background:#040d06;border-bottom:1px solid #1a2a1a;
    padding:10px 16px;display:grid;
    grid-template-columns:auto 1fr auto auto auto;gap:16px;align-items:center;">

    <div style="color:#4ade80;font-size:16px;font-weight:900;letter-spacing:4px;
      text-shadow:0 0 12px rgba(74,222,128,0.6);">⚔ SNAPQUEST</div>

    <!-- Minimap -->
    <div style="display:flex;align-items:center;gap:0;">{map_slots}</div>

    <!-- Room indicator -->
    <div style="text-align:center;">
      <div style="color:{diff_color};font-size:9px;letter-spacing:3px;">{diff}</div>
      <div style="color:#4a6a4a;font-size:10px;">ROOM {idx+1}/{total_rooms}</div>
    </div>

    <!-- HP -->
    <div style="min-width:140px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
        <span style="color:#ff5555;font-size:10px;letter-spacing:2px;">HP</span>
        <span style="color:{hp_color};font-size:10px;">{hp}/{max_hp}</span>
      </div>
      <div style="height:6px;background:#1a0404;border:1px solid #3a1010;">
        <div style="height:100%;width:{hp_pct}%;background:{hp_color};transition:width 0.4s;"></div>
      </div>
    </div>

    <!-- Level / XP -->
    <div style="min-width:100px;text-align:right;">
      <div style="color:#fbbf24;font-size:10px;letter-spacing:2px;">LVL {level}</div>
      <div style="color:#4a6a4a;font-size:10px;">{xp % 100}/100 XP</div>
    </div>
  </div>

  <!-- MAIN CONTENT -->
  <div style="flex:1;display:grid;grid-template-columns:260px 1fr 240px;gap:0;">

    <!-- LEFT PANEL: Class + Inventory -->
    <div style="border-right:1px solid #1a2a1a;background:#030806;
      display:flex;flex-direction:column;overflow:hidden;">

      <!-- Class card -->
      <div style="border-bottom:1px solid #1a2a1a;padding:14px;">
        <div style="text-align:center;margin-bottom:10px;">
          <div style="font-family:Courier New,monospace;font-size:12px;line-height:1.5;
            color:{cd["accent"]};text-shadow:0 0 6px {cd["accent"]};margin-bottom:4px;">
            {"<br>".join(_h.escape(r) for r in cd["art"])}
          </div>
          <div style="color:{cd["color"]};font-size:13px;font-weight:bold;letter-spacing:3px;">
            {cls.upper()}</div>
          <div style="color:{cd["accent"]};font-size:10px;opacity:0.7;">{_h.escape(cd["tagline"])}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
          {"".join(f'<div style="background:#020705;padding:6px 4px;text-align:center;border:1px solid #1a2a1a;"><div style="color:{cd["accent"]};font-size:14px;font-weight:bold;">{v}</div><div style="color:#2a4a2a;font-size:9px;">{k}</div></div>' for k,v in cd["stats"].items())}
        </div>
      </div>

      <!-- Inventory -->
      <div style="flex:1;overflow-y:auto;padding:12px;">
        <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:10px;">
          INVENTORY
        </div>
        {inv_html}
      </div>
    </div>

    <!-- CENTER: Scene + Chronicle -->
    <div style="display:flex;flex-direction:column;overflow:hidden;">

      <!-- Scene name -->
      <div style="border-bottom:1px solid #1a2a1a;padding:10px 16px;
        background:#040d06;display:flex;align-items:center;justify-content:space-between;">
        <div>
          <span style="color:#1e3d28;font-size:10px;letter-spacing:3px;">LOCATION  ·  </span>
          <span style="color:#a0c4a8;font-size:13px;letter-spacing:2px;">
            {_h.escape(scene_name)}</span>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">{monster_html}</div>
      </div>

      {boss_panel}

      <!-- Story feed -->
      <div style="flex:1;overflow-y:auto;padding:16px;
        background:#030806;
        background-image:repeating-linear-gradient(0deg,transparent,transparent 3px,
          rgba(74,222,128,0.008) 3px,rgba(74,222,128,0.008) 4px);">
        <div style="max-width:100%;line-height:1.0;">
          {story_lines}
        </div>
      </div>

      <!-- Action zone -->
      <div style="border-top:1px solid #1a2a1a;padding:12px 16px;background:#040d06;">
        {advance_btn}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
          {choice_btns}
        </div>
        <div style="display:flex;gap:8px;">
          <input id="sq-custom-input" type="text"
            placeholder='Custom action — "attack", "search", "use ember flask"...'
            style="flex:1;background:#030806;border:1px solid #1a3a1a;color:#a0c4a8;
              font-family:Courier New,monospace;font-size:12px;padding:10px 12px;"
            onkeydown="if(event.key==='Enter')window.__sq_do_action(this.value)">
          <button onclick="window.__sq_do_action(document.getElementById('sq-custom-input').value)"
            style="background:#040d06;border:1px solid #2a5a2a;color:#4ade80;
              font-family:Courier New,monospace;font-size:12px;letter-spacing:2px;
              padding:10px 16px;cursor:pointer;">⚔ ACT</button>
        </div>
      </div>
    </div>

    <!-- RIGHT PANEL: Scene atmosphere + voice -->
    <div style="border-left:1px solid #1a2a1a;background:#030806;
      display:flex;flex-direction:column;overflow:hidden;">

      <!-- Atmosphere -->
      <div style="padding:14px;border-bottom:1px solid #1a2a1a;flex:1;overflow-y:auto;">
        <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:10px;">
          ATMOSPHERE
        </div>
        <div style="color:#2a5a38;font-size:12px;line-height:1.8;font-style:italic;">
          {_h.escape(room.get("atmosphere") or room.get("scene_description") or "The dungeon holds its breath...")}
        </div>
        {f'<div style="margin-top:12px;border-top:1px solid #1a2a1a;padding-top:10px;color:#1e3d28;font-size:10px;letter-spacing:2px;margin-bottom:6px;">ROOM LORE</div><div style="color:#1a3020;font-size:11px;line-height:1.7;">Difficulty: <span style="color:{diff_color};">{diff}</span><br>Enemies: {"Active" if room.get("enemy_alive") else "Defeated"}<br>Room: {idx+1} of {total_rooms}</div>' if True else ""}
      </div>

      <!-- Voice -->
      <div id="sq-voice-section" style="padding:14px;border-top:1px solid #1a2a1a;">
        <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:10px;">
          VOICE COMMAND
        </div>
        <div id="sq-voice-placeholder" style="color:#1a3020;font-size:11px;text-align:center;
          padding:16px 0;">🎙 Use the mic below</div>
      </div>
    </div>
  </div>
</div>"""

# ════════════════════════════════════════════════════════════════════════════
# GRADIO APP
# ════════════════════════════════════════════════════════════════════════════

_HIDE_GRADIO_CSS = """
/* Hide all Gradio chrome */
.gradio-container > .main > .wrap > .gap > *:not(#sq-root-row) { display: none !important; }
footer { display: none !important; }
.gr-prose { display: none !important; }
body, .gradio-container {
  background: #03060a !important;
  margin: 0 !important; padding: 0 !important;
  font-family: 'Courier New', monospace !important;
}
#sq-root-row { max-width: 100% !important; padding: 0 !important; }
/* Make Gradio image uploads actually work but stay hidden */
.sq-hidden { position: absolute !important; opacity: 0 !important; pointer-events: none !important; width: 1px !important; height: 1px !important; overflow: hidden !important; }
"""

with gr.Blocks(css=_HIDE_GRADIO_CSS, title="SNAPQUEST") as demo:
    # ── State ──────────────────────────────────────────────────────────────
    game_state   = gr.State({})
    photo_data   = gr.State([])          # list of {path, objects}
    sel_class    = gr.State("Swordsman")
    current_screen = gr.State("s1")      # s1 / s2 / s3
    loot_pending = gr.State([])

    # ── Main display ───────────────────────────────────────────────────────
    with gr.Row(elem_id="sq-root-row"):
        main_html = gr.HTML(_screen1_html([]))

    # ── Hidden Gradio file inputs (real upload widgets, invisible) ─────────
    with gr.Row(elem_classes=["sq-hidden"]):
        hf_photo1 = gr.Image(type="filepath", label="p1")
        hf_photo2 = gr.Image(type="filepath", label="p2")
        hf_photo3 = gr.Image(type="filepath", label="p3")

    # ── Hidden bridge components ────────────────────────────────────────────
    with gr.Row(elem_classes=["sq-hidden"]):
        bridge_action   = gr.Textbox(label="action")
        bridge_trigger  = gr.Button("trigger")
        bridge_screen   = gr.Textbox(label="screen")
        bridge_scr_btn  = gr.Button("scr")
        bridge_class_in = gr.Textbox(label="class_sel")
        bridge_class_btn = gr.Button("cls")

    # ── Voice (kept visible in right panel via JS injection) ───────────────
    with gr.Row(elem_classes=["sq-hidden"]):
        voice_input  = gr.Audio(sources=["microphone"], type="filepath", label="mic")
        voice_output = gr.Audio(label="dm", autoplay=True)
        voice_btn    = gr.Button("voice")
        transcribed  = gr.Textbox(label="trans")

    # ── JS bridge ──────────────────────────────────────────────────────────
    # Inject JS after page load via gr.HTML
    js_bridge = gr.HTML("""
<script>
// Wait for Gradio to be ready
function sqReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn);
  } else { fn(); }
}

sqReady(function() {
  // Screen navigation
  window.__sq_proceed_to_class = function() {
    var tb = document.querySelector('textarea[data-testid="screen"]') ||
             Array.from(document.querySelectorAll('textarea')).find(t => t.closest('label') && t.closest('label').textContent.includes('screen'));
    var btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'scr');
    if (!tb || !btn) {
      // fallback: try by index
      var tbs = document.querySelectorAll('textarea');
      tb = tbs[1]; // bridge_screen
      btn = document.querySelectorAll('button')[1];
    }
    if (tb) { tb.value = 's2'; tb.dispatchEvent(new Event('input', {bubbles:true})); }
    setTimeout(function(){ if (btn) btn.click(); }, 100);
  };

  window.__sq_go_back = function() {
    var tbs = document.querySelectorAll('.sq-hidden textarea');
    var btns = document.querySelectorAll('.sq-hidden button');
    var tb = tbs[1]; var btn = btns[1];
    if (tb) { tb.value = 's1'; tb.dispatchEvent(new Event('input', {bubbles:true})); }
    setTimeout(function(){ if (btn) btn.click(); }, 100);
  };

  window.__sq_select_class = function(cls) {
    var tbs = document.querySelectorAll('.sq-hidden textarea');
    var btns = document.querySelectorAll('.sq-hidden button');
    var tb = tbs[2]; var btn = btns[2];
    if (tb) { tb.value = cls; tb.dispatchEvent(new Event('input', {bubbles:true})); }
    setTimeout(function(){ if (btn) btn.click(); }, 100);
  };

  window.__sq_start_dungeon = function() {
    var tbs = document.querySelectorAll('.sq-hidden textarea');
    var btns = document.querySelectorAll('.sq-hidden button');
    var tb = tbs[1]; var btn = btns[1];
    if (tb) { tb.value = 's3_start'; tb.dispatchEvent(new Event('input', {bubbles:true})); }
    setTimeout(function(){ if (btn) btn.click(); }, 150);
  };

  window.__sq_do_action = function(action) {
    if (!action || !action.trim()) return;
    var tbs = document.querySelectorAll('.sq-hidden textarea');
    var btns = document.querySelectorAll('.sq-hidden button');
    var tb = tbs[0]; var btn = btns[0];
    if (tb) { tb.value = action; tb.dispatchEvent(new Event('input', {bubbles:true})); }
    // Clear custom input
    var inp = document.getElementById('sq-custom-input');
    if (inp) inp.value = '';
    setTimeout(function(){ if (btn) btn.click(); }, 100);
  };
});
</script>
""")

    # ════════════════════════════════════════════════════════════════════════
    # PHOTO UPLOAD HANDLERS
    # ════════════════════════════════════════════════════════════════════════

    def _on_photo_upload(path, slot_idx, photo_data_cur):
        """When a hidden photo widget gets a file, analyze it and update screen."""
        from vision import analyze_scene
        pd = list(photo_data_cur) if photo_data_cur else []
        while len(pd) <= slot_idx:
            pd.append({})
        if path:
            try:
                # Quick object scan — use current class or default
                scene = analyze_scene(path, "Rogue")
                pd[slot_idx] = {"path": path, "objects": scene.get("objects_found", [])}
            except Exception:
                pd[slot_idx] = {"path": path, "objects": ["unknown object"]}
        else:
            pd[slot_idx] = {}
        return pd, _screen1_html(pd)

    hf_photo1.change(lambda p, pd: _on_photo_upload(p, 0, pd),
                     inputs=[hf_photo1, photo_data],
                     outputs=[photo_data, main_html], api_name=False)
    hf_photo2.change(lambda p, pd: _on_photo_upload(p, 1, pd),
                     inputs=[hf_photo2, photo_data],
                     outputs=[photo_data, main_html], api_name=False)
    hf_photo3.change(lambda p, pd: _on_photo_upload(p, 2, pd),
                     inputs=[hf_photo3, photo_data],
                     outputs=[photo_data, main_html], api_name=False)

    # ════════════════════════════════════════════════════════════════════════
    # SCREEN NAVIGATION
    # ════════════════════════════════════════════════════════════════════════

    def _nav(screen_cmd, photo_data_cur, sel_class_cur, game_state_cur):
        pd = photo_data_cur or []
        cls = sel_class_cur or "Swordsman"
        s = game_state_cur or {}

        if screen_cmd == "s1":
            return "s1", _screen1_html(pd), s, []

        elif screen_cmd == "s2":
            return "s2", _screen2_html(cls), s, []

        elif screen_cmd == "s3_start":
            # Build dungeon
            paths = [d["path"] for d in pd if d.get("path")]
            if not paths:
                return "s2", _screen2_html(cls), s, []
            try:
                state = start_photo_game(paths, cls)
                html_out = _screen3_html(state, _format_story(state), None, None)
                return "s3", html_out, state, []
            except Exception as exc:
                err_html = (
                    f'<div style="color:#ff5555;padding:40px;font-family:Courier New,monospace;">'
                    f'Error building dungeon: {_h.escape(str(exc))}</div>'
                )
                return "s2", err_html, s, []

        return "s1", _screen1_html(pd), s, []

    bridge_scr_btn.click(
        _nav,
        inputs=[bridge_screen, photo_data, sel_class, game_state],
        outputs=[current_screen, main_html, game_state, loot_pending],
        api_name=False,
    )

    # ════════════════════════════════════════════════════════════════════════
    # CLASS SELECTION
    # ════════════════════════════════════════════════════════════════════════

    def _on_class_click(cls):
        return cls, _screen2_html(cls)

    bridge_class_btn.click(
        _on_class_click,
        inputs=[bridge_class_in],
        outputs=[sel_class, main_html],
        api_name=False,
    )

    # ════════════════════════════════════════════════════════════════════════
    # GAME ACTION
    # ════════════════════════════════════════════════════════════════════════

    def _format_story(state) -> str:
        s = _safe_state(state)
        if not s.get("rooms"):
            return "The dungeon awaits..."
        room = _cur_room(s)
        scene_name = room.get("scene_name", "Unknown")
        diff = room.get("difficulty", "").upper()
        sym = {"EASY": "◆", "MEDIUM": "◈", "HARD": "⬡"}.get(diff, "◆")
        lines = [f"{'─'*5} {sym} {scene_name} {sym} {'─'*5}", ""]
        lines.append(room.get("scene_description", ""))
        history = s.get("history", [])
        if history:
            lines.append("\n── Chronicle ──")
            for entry in history[-8:]:
                act = entry.get("action", "")
                resp = entry.get("response", {})
                st = resp.get("story", "")
                lines.append(f"\n▷ {act}")
                if st:
                    lines.append(st)
        return "\n".join(str(l) for l in lines if l is not None)

    def _on_action(action, state, cur_screen):
        s = _safe_state(state)
        if cur_screen != "s3" or not s.get("rooms"):
            return state, main_html, None, []
        if not action or not action.strip():
            return state, _screen3_html(s, _format_story(s), None, None), None, []
        try:
            new_state, parsed = take_photo_action(s, action.strip())
            # Check if room just cleared → roll loot
            room = _cur_room(new_state)
            loot = []
            if room.get("cleared") and not _cur_room(s).get("cleared"):
                n = 3 if room.get("is_boss") else 2
                loot = _roll_loot(n)
                # Add to inventory
                new_state["inventory"] = new_state.get("inventory", []) + loot
            story = _format_story(new_state)
            # Voice
            audio = None
            try:
                txt = clean_for_speech(parsed)
                if txt:
                    audio = speak(txt)
            except Exception:
                pass
            return new_state, _screen3_html(new_state, story, parsed, loot if loot else None), audio, loot
        except Exception as exc:
            s2 = _safe_state(state)
            err_story = _format_story(s2) + f"\n\n⚠ {str(exc)}"
            return state, _screen3_html(s2, err_story, None, None), None, []

    bridge_trigger.click(
        _on_action,
        inputs=[bridge_action, game_state, current_screen],
        outputs=[game_state, main_html, voice_output, loot_pending],
        api_name=False,
    )

    # ════════════════════════════════════════════════════════════════════════
    # VOICE
    # ════════════════════════════════════════════════════════════════════════

    def _on_voice(audio_path, state, cur_screen):
        if not audio_path:
            return state, main_html, None, "", []
        try:
            text = transcribe_audio(audio_path)
        except Exception:
            text = ""
        new_state, new_html, audio, loot = _on_action(text, state, cur_screen)
        return new_state, new_html, audio, text, loot

    voice_btn.click(
        _on_voice,
        inputs=[voice_input, game_state, current_screen],
        outputs=[game_state, main_html, voice_output, transcribed, loot_pending],
        api_name=False,
    )