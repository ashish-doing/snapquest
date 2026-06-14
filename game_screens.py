"""game_screens.py — HTML builders for SnapQuest's 3 game screens.

All screens are rendered as raw HTML strings injected via gr.HTML.
No Gradio widgets are visible anywhere in these screens.
"""
from __future__ import annotations
import html as _h
import json

from game_data import CHARACTER_CLASSES, CLASS_DATA, LOOT_TIERS

# ════════════════════════════════════════════════════════════════════════════
# SHARED CSS + JS BRIDGE (injected once, lives across screens)
# ════════════════════════════════════════════════════════════════════════════

BASE_CSS = """
<style>
* { box-sizing: border-box; }
.sq-app {
  font-family: 'Courier New', Courier, monospace;
  background: #03060a;
  color: #d4eedd;
  min-height: 100vh;
  margin: -16px;
  padding: 0;
}
.sq-app .scanlines {
  position: absolute; inset: 0; pointer-events: none;
  background: repeating-linear-gradient(0deg, transparent, transparent 3px,
    rgba(74,222,128,0.012) 3px, rgba(74,222,128,0.012) 4px);
}
.sq-btn-primary {
  font-family: 'Courier New', monospace; font-size: 14px; letter-spacing: 5px;
  padding: 16px 0; width: 100%; cursor: pointer; text-transform: uppercase;
  border: 1px solid #4ade80; color: #4ade80;
  background: linear-gradient(90deg,#0a2a10,#0f3818);
  box-shadow: 0 0 24px rgba(74,222,128,0.15);
  transition: all 0.2s;
}
.sq-btn-primary:hover { box-shadow: 0 0 36px rgba(74,222,128,0.3); }
.sq-btn-disabled {
  font-family: 'Courier New', monospace; font-size: 14px; letter-spacing: 5px;
  padding: 16px 0; width: 100%; cursor: not-allowed; text-transform: uppercase;
  border: 1px solid #1a2a1a; color: #2a4a2a; background: #050a06;
}
.sq-upload-slot {
  border: 1px solid #1a2a1a; background: #030806; padding: 16px;
  min-height: 130px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; cursor: pointer;
  transition: border-color 0.2s; text-align: center; position: relative;
}
.sq-upload-slot:hover { border-color: #2a5a38; }
.sq-upload-slot.has-photo {
  border-color: #2a5a38; align-items: flex-start; justify-content: flex-start;
  box-shadow: 0 0 20px rgba(74,222,128,0.06);
}
.sq-upload-slot img { width: 100%; height: 70px; object-fit: cover; margin-bottom: 8px; border: 1px solid #1a2a1a; }
.sq-badge {
  border: 1px solid #1e3d28; padding: 4px 12px; font-size: 10px;
  color: #2a5a38; letter-spacing: 2px;
}
.sq-badge-red { border-color: #5a1a1a; color: #aa3333; }
.sq-tag {
  border: 1px solid #2a4a2a; padding: 2px 8px; font-size: 10px;
  color: #4ade80; margin: 2px; display: inline-block;
}
@keyframes bossGlow {
  from { box-shadow: 0 0 16px rgba(255,85,85,0.25); }
  to   { box-shadow: 0 0 40px rgba(255,85,85,0.6); }
}
@keyframes loadingPulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
</style>
"""

# JS bridge: sends commands from HTML buttons to Python via a hidden textbox + button
JS_BRIDGE = ""  # JS now lives in gr.Blocks(head=...) — see ui_photo.py

# ════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — LANDING / UPLOAD
# ════════════════════════════════════════════════════════════════════════════

def screen1_html(photos: list[dict], loading: bool = False) -> str:
    """photos: list of 0-3 dicts {path, objects, name}"""
    slots_html = ""
    room_labels = ["ENTRY HALL", "INNER CHAMBER", "BOSS LAIR"]
    for i in range(3):
        p = photos[i] if i < len(photos) else {}
        has = bool(p.get("path"))
        label = room_labels[i]
        opt_tag = "" if i == 0 else " (optional)"

        if has:
            objs = p.get("objects", [])
            tags = "".join('<span class="sq-tag">{}</span>'.format(_h.escape(o)) for o in objs)
            boss_note = ""
            if i == 2 and objs:
                boss_note = (
                    '<div style="margin-top:8px;border:1px solid #ff5555;padding:4px 8px;'
                    'background:#0f0303;color:#ff5555;font-size:10px;letter-spacing:2px;">'
                    '☠ BOSS: {} GUARDIAN</div>'
                ).format(_h.escape(objs[0].upper()) if objs else "UNKNOWN")
            inner = (
                '<img src="{src}">'
                '<div style="color:#4ade80;font-size:10px;letter-spacing:2px;margin-bottom:6px;">✓ LOADED</div>'
                '<div>{tags}</div>{boss}'
            ).format(src=p.get("path", ""), tags=tags, boss=boss_note)
            cls_extra = " has-photo"
        else:
            inner = (
                '<div style="color:#1e3d28;font-size:32px;margin-bottom:6px;">+</div>'
                '<div style="color:#2a5a38;font-size:11px;letter-spacing:2px;">UPLOAD<br>{label}</div>'
                '<div style="color:#1a3020;font-size:10px;margin-top:4px;">{opt}</div>'
            ).format(label=label, opt=opt_tag)
            cls_extra = ""

        slots_html += (
            '<div class="sq-upload-slot{extra}" onclick="window.__sq_pick_file({i})">'
            '<div style="color:#2a5a38;font-size:9px;letter-spacing:3px;margin-bottom:8px;'
            'position:absolute;top:8px;left:12px;">ROOM 0{n} · {label}</div>'
            '<div style="margin-top:24px;width:100%;">{inner}</div>'
            '<input type="file" id="sq-file-input-{i}" accept="image/*" style="display:none"'
            ' onchange="window.__sq_handle_file({i}, this)">'
            '</div>'
        ).format(extra=cls_extra, i=i, n=i+1, label=label, inner=inner)

    n_loaded = sum(1 for p in photos if p.get("path"))
    can_proceed = n_loaded >= 1 and not loading

    if loading:
        btn_html = (
            '<div class="sq-btn-disabled" style="animation:loadingPulse 1.2s infinite;">'
            '⚔ ANALYZING PHOTOS... MINICPM-V 4.6 READING YOUR WORLD</div>'
        )
    elif can_proceed:
        n_label = {1: "1-room dungeon", 2: "2-room dungeon", 3: "3-room dungeon (with boss)"}.get(n_loaded, "")
        btn_html = (
            '<button class="sq-btn-primary" onclick="window.__sq_goto_class()">'
            '▶  CHOOSE YOUR CLASS  →</button>'
            '<div style="text-align:center;color:#1e3d28;font-size:10px;letter-spacing:2px;margin-top:8px;">'
            '{} ready</div>'
        ).format(n_label)
    else:
        btn_html = '<div class="sq-btn-disabled">UPLOAD A PHOTO TO CONTINUE</div>'

    return BASE_CSS + JS_BRIDGE + """
<div class="sq-app">
  <div style="position:relative;">
    <div class="scanlines"></div>
    <div style="position:relative;width:100%;background:linear-gradient(180deg,#040e07 0%,#03060a 100%);
      border-bottom:1px solid #1a2a1a;padding:40px 20px 32px;text-align:center;">
      <div style="color:#4ade80;font-size:42px;font-weight:900;letter-spacing:12px;
        text-shadow:0 0 20px rgba(74,222,128,0.9),0 0 60px rgba(74,222,128,0.4);
        margin-bottom:6px;">S N A P Q U E S T</div>
      <div style="color:#1a5a28;font-size:12px;letter-spacing:6px;margin-bottom:24px;">
        YOUR ROOM · YOUR DUNGEON · MINICPM-V 4.6</div>
      <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-bottom:28px;">
        <span class="sq-badge">1.3B PARAMS</span>
        <span class="sq-badge">MODAL A10G GPU</span>
        <span class="sq-badge">MULTI-ROOM DUNGEON</span>
        <span class="sq-badge sq-badge-red">☠ BOSS FIGHTS</span>
      </div>
      <div style="max-width:540px;margin:0 auto;color:#2a5a38;font-size:13px;line-height:1.8;">
        Upload photos of any real space.<br>
        MiniCPM-V reads every object inside them.<br>
        Your <span style="color:#4ade80;">bookshelf</span> becomes the Archive of Tomes.
        Your <span style="color:#ff5555;">lamp becomes the boss.</span>
      </div>
    </div>
  </div>

  <div style="max-width:760px;margin:0 auto;padding:32px 20px 0;">
    <div style="color:#2a5a38;font-size:10px;letter-spacing:4px;margin-bottom:16px;">
      ▸ UPLOAD PHOTOS ( 1 MINIMUM · 3 FOR FULL DUNGEON )
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
      """ + slots_html + """
    </div>

    <div style="border:1px solid #1a2a1a;background:#040d06;padding:16px 20px;margin-bottom:20px;">
      <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:12px;">HOW IT WORKS</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
        <div style="text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">📸</div>
          <div style="color:#2a5a38;font-size:11px;line-height:1.6;">AI reads every object in your photo</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">🏰</div>
          <div style="color:#2a5a38;font-size:11px;line-height:1.6;">Objects become dungeon elements &amp; monsters</div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:24px;margin-bottom:6px;">☠</div>
          <div style="color:#aa3333;font-size:11px;line-height:1.6;">Last photo's main object is your final boss</div>
        </div>
      </div>
    </div>

    """ + btn_html + """
  </div>
</div>"""


# ════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — CLASS SELECTION
# ════════════════════════════════════════════════════════════════════════════

def screen2_html(selected_class: str | None, dungeon_summary: str = "") -> str:
    cards = ""
    for cls in CHARACTER_CLASSES:
        d = CLASS_DATA[cls]
        is_sel = (cls == selected_class)
        border = "2px solid " + d["accent"] if is_sel else "1px solid #1a2a1a"
        bg = "#040d06" if is_sel else "#030806"
        shadow = "0 0 30px " + d["accent"] + "33" if is_sel else "none"

        stats_html = "".join(
            '<div style="text-align:center;"><div style="color:{accent};font-size:16px;'
            'font-weight:bold;">{v}</div><div style="color:#2a4a2a;font-size:9px;'
            'letter-spacing:1px;">{k}</div></div>'.format(accent=d["accent"], v=v, k=k)
            for k, v in d["stats"].items()
        )
        perks_html = "".join(
            '<div style="color:#4a6a4a;font-size:11px;padding:4px 0;'
            'border-bottom:1px solid #1a2a1a;">▸ {}</div>'.format(_h.escape(p))
            for p in d["perks"]
        )
        sel_badge = (
            '<div style="text-align:center;color:{};font-size:11px;letter-spacing:3px;'
            'margin-top:10px;">✓ SELECTED</div>'.format(d["accent"])
        ) if is_sel else ""

        cards += (
            '<div onclick="window.__sq_select_class(\'{cls}\')" '
            'style="border:{border};background:{bg};padding:20px 16px;cursor:pointer;'
            'transition:all 0.2s;box-shadow:{shadow};">'
            '<div style="text-align:center;margin-bottom:14px;">'
            '<div style="font-size:28px;">{icon}</div>'
            '<div style="color:{color};font-size:14px;font-weight:bold;letter-spacing:3px;'
            'margin-top:6px;">{cls_upper}</div>'
            '<div style="color:{accent};font-size:10px;letter-spacing:1px;margin-top:2px;'
            'opacity:0.8;">{tagline}</div>'
            '</div>'
            '<div style="color:#4a6a4a;font-size:11px;line-height:1.6;margin-bottom:12px;'
            'border-top:1px solid #1a2a1a;padding-top:10px;">{desc}</div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:4px;'
            'margin-bottom:12px;background:#020705;padding:10px 4px;">{stats}</div>'
            '<div style="margin-bottom:10px;">{perks}</div>'
            '<div style="border:1px solid #1a2a1a;padding:6px 8px;color:#2a4a2a;'
            'font-size:10px;letter-spacing:1px;font-style:italic;">"{playstyle}"</div>'
            '{sel_badge}'
            '</div>'
        ).format(
            cls=cls, border=border, bg=bg, shadow=shadow, icon=d["icon"],
            color=d["color"], cls_upper=cls.upper(), accent=d["accent"],
            tagline=_h.escape(d["tagline"]), desc=_h.escape(d["desc"]),
            stats=stats_html, perks=perks_html, playstyle=_h.escape(d["playstyle"]),
            sel_badge=sel_badge,
        )

    can_start = bool(selected_class)
    if can_start:
        btn_html = '<button class="sq-btn-primary" onclick="window.__sq_start_dungeon()">▶  ENTER THE DUNGEON  →</button>'
    else:
        btn_html = '<div class="sq-btn-disabled">SELECT A CLASS FIRST</div>'

    return BASE_CSS + JS_BRIDGE + """
<div class="sq-app">
  <div style="border-bottom:1px solid #1a2a1a;background:#040d06;padding:16px 24px;
    display:flex;align-items:center;justify-content:space-between;">
    <span style="color:#4ade80;font-size:20px;font-weight:900;letter-spacing:6px;
      text-shadow:0 0 16px rgba(74,222,128,0.7);">⚔ SNAPQUEST</span>
    <button onclick="window.__sq_go_back('s1')" style="background:none;border:1px solid #1a2a1a;
      color:#2a5a38;font-family:Courier New,monospace;font-size:11px;letter-spacing:2px;
      padding:6px 14px;cursor:pointer;">← BACK</button>
  </div>
  <div style="max-width:1100px;margin:0 auto;padding:28px 20px 40px;">
    <div style="text-align:center;margin-bottom:8px;">
      <div style="color:#4ade80;font-size:18px;letter-spacing:6px;margin-bottom:4px;">CHOOSE YOUR CLASS</div>
      <div style="color:#1e3d28;font-size:11px;letter-spacing:3px;">YOUR LENS CHANGES HOW THE DUNGEON REVEALS ITSELF</div>
    </div>
    """ + ('<div style="text-align:center;color:#2a5a38;font-size:11px;margin-bottom:20px;">' + dungeon_summary + '</div>' if dungeon_summary else '<div style="margin-bottom:20px;"></div>') + """
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:28px;">""" + cards + """</div>
    """ + btn_html + """
  </div>
</div>"""


# ════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — DUNGEON COMBAT
# ════════════════════════════════════════════════════════════════════════════

def _inv_html(inventory: list) -> str:
    if not inventory:
        return '<div style="color:#4a5568;font-size:12px;">Empty — explore to find loot</div>'
    rows = ""
    for item in inventory:
        if isinstance(item, dict):
            td = LOOT_TIERS.get(item.get("tier", "common"), LOOT_TIERS["common"])
            rows += (
                '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;'
                'border-bottom:1px solid #1a2a1a;">'
                '<span style="font-size:16px;">{icon}</span>'
                '<div><div style="color:{color};font-size:11px;text-shadow:{glow};'
                'font-weight:bold;">{name}</div>'
                '<div style="color:#4a6a4a;font-size:10px;">{stat}</div></div>'
                '<div style="margin-left:auto;font-size:9px;color:{color};opacity:0.7;">{label}</div>'
                '</div>'
            ).format(
                icon=item.get("icon", "📦"), color=td["color"], glow=td["glow"],
                name=_h.escape(item.get("name", "?")), stat=_h.escape(item.get("stat", "")),
                label=td["label"],
            )
        else:
            rows += '<div style="color:#9ca3af;font-size:12px;padding:3px 0;">• {}</div>'.format(_h.escape(str(item)))
    return rows


def _loot_popup_html(items: list[dict]) -> str:
    if not items:
        return ""
    cards = ""
    for item in items:
        td = LOOT_TIERS.get(item.get("tier", "common"), LOOT_TIERS["common"])
        cards += (
            '<div style="border:1px solid {color};background:#080f08;padding:12px 16px;'
            'min-width:140px;text-align:center;box-shadow:{glow};">'
            '<div style="font-size:28px;margin-bottom:6px;">{icon}</div>'
            '<div style="color:{color};font-size:10px;letter-spacing:2px;margin-bottom:4px;">{label}</div>'
            '<div style="color:#d4eedd;font-size:13px;font-weight:bold;margin-bottom:4px;">{name}</div>'
            '<div style="color:#6b9a75;font-size:11px;">{stat}</div>'
            '</div>'
        ).format(
            color=td["color"], glow=td["glow"], icon=item.get("icon", "📦"),
            label=td["label"], name=_h.escape(item.get("name", "?")),
            stat=_h.escape(item.get("stat", "")),
        )
    return (
        '<div id="loot-popup" style="position:fixed;inset:0;background:rgba(0,0,0,0.85);'
        'z-index:9999;display:flex;flex-direction:column;align-items:center;'
        'justify-content:center;font-family:Courier New,monospace;">'
        '<div style="color:#fbbf24;font-size:22px;letter-spacing:6px;margin-bottom:24px;'
        'text-shadow:0 0 20px rgba(251,191,36,0.8);">✦ LOOT FOUND ✦</div>'
        '<div style="display:flex;gap:16px;flex-wrap:wrap;justify-content:center;'
        'margin-bottom:28px;">{cards}</div>'
        '<button onclick="document.getElementById(\'loot-popup\').remove()" '
        'style="background:#0a1a0a;border:1px solid #4ade80;color:#4ade80;'
        'font-family:Courier New,monospace;font-size:14px;letter-spacing:4px;'
        'padding:12px 32px;cursor:pointer;">COLLECT ALL</button>'
        '</div>'
    ).format(cards=cards)


def screen3_html(state: dict, story: str, loot_items: list | None = None) -> str:
    rooms = state.get("rooms", [])
    idx = state.get("room_index", 0)
    room = rooms[min(idx, len(rooms)-1)] if rooms else {}
    total_rooms = len(rooms)
    cls = state.get("character_class", "Swordsman")
    cd = CLASS_DATA.get(cls, CLASS_DATA["Swordsman"])

    hp = int(state.get("hp", 100))
    max_hp = int(state.get("max_hp", 100))
    xp = int(state.get("xp", 0))
    level = 1 + xp // 100
    hp_pct = max(0, min(100, int(hp / max(max_hp, 1) * 100)))
    hp_color = "#ff5555" if hp_pct < 30 else "#facc15" if hp_pct < 60 else "#4ade80"

    is_boss = room.get("is_boss", False)
    boss = room.get("boss") if is_boss else None
    boss_alive = boss.get("alive", True) if boss else False

    choices = state.get("current_choices", ["Look around", "Move forward", "Hold position"])
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
            '<div style="width:26px;height:26px;border:{bc};color:{c};display:flex;'
            'align-items:center;justify-content:center;font-size:12px;background:#030806;">{sym}</div>'
        ).format(bc=bc, c=c, sym=sym)
        if i < len(rooms) - 1:
            map_slots += '<div style="width:12px;height:1px;background:#1a2a1a;align-self:center;"></div>'

    # Story lines
    story_lines = ""
    for line in (story or "").split("\n"):
        esc = _h.escape(line)
        if line.startswith("─") or line.startswith("═"):
            story_lines += '<div style="color:#1e3d28;margin:6px 0;">{}</div>'.format(esc)
        elif line.startswith("▷") or line.startswith(">"):
            story_lines += '<div style="color:#60a5fa;margin-top:8px;">{}</div>'.format(esc)
        elif line.startswith("⚔") or line.startswith("💀"):
            story_lines += '<div style="color:#ff5555;font-weight:bold;">{}</div>'.format(esc)
        elif line.startswith("✅") or line.startswith("🏆"):
            story_lines += '<div style="color:#4ade80;font-weight:bold;">{}</div>'.format(esc)
        elif line.startswith("💰") or line.startswith("✨"):
            story_lines += '<div style="color:#fbbf24;">{}</div>'.format(esc)
        elif line.strip():
            story_lines += '<div style="color:#a0c4a8;line-height:1.7;">{}</div>'.format(esc)
        else:
            story_lines += '<div style="height:6px;"></div>'

    # Choice buttons
    choice_btns = ""
    is_boss_active = is_boss and boss_alive
    for i, c in enumerate(choices[:3]):
        if is_boss_active:
            border_c, hover_c, text_c = "#5a1a1a", "#ff5555", "#ff8888"
        else:
            border_c, hover_c, text_c = "#1a3a1a", "#4ade80", "#a0c4a8"
        num = ["①", "②", "③"][i]
        choice_btns += (
            '<button onclick="window.__sq_action({jstext})" '
            'style="background:#040d06;border:1px solid {border_c};color:{text_c};'
            'font-family:Courier New,monospace;font-size:12px;padding:12px 10px;'
            'cursor:pointer;width:100%;text-align:left;letter-spacing:0.5px;'
            'transition:all 0.18s;line-height:1.4;" '
            'onmouseover="this.style.borderColor=\'{hover_c}\'" '
            'onmouseout="this.style.borderColor=\'{border_c}\'">'
            '<span style="opacity:0.5;margin-right:8px;">{num}</span>{ctext}'
            '</button>'
        ).format(
            jstext=json.dumps(c), border_c=border_c, hover_c=hover_c, text_c=text_c,
            num=num, ctext=_h.escape(c),
        )

    # Monster tags
    monster_html = ""
    for obj in objects:
        if is_boss and objects and obj == objects[0] and boss:
            monster_html += (
                '<div style="border:1px solid #ff5555;background:#0a0202;padding:6px 12px;'
                'font-size:11px;color:#ff5555;box-shadow:0 0 12px rgba(255,85,85,0.2);">'
                '☠ {}</div>'
            ).format(_h.escape(obj.upper()))
        else:
            monster_html += (
                '<div style="border:1px solid #1a3a1a;background:#030806;padding:4px 10px;'
                'font-size:11px;color:#4a6a4a;">◆ {}</div>'
            ).format(_h.escape(obj))

    # Boss panel
    boss_panel = ""
    if is_boss and boss:
        b_hp = boss.get("hp", 0)
        b_max = boss.get("max_hp", 100)
        b_pct = max(0, min(100, int(b_hp / max(b_max, 1) * 100)))
        b_name = _h.escape(boss.get("name", "Unknown"))
        if boss_alive:
            boss_panel = (
                '<div style="border:2px solid #ff5555;background:#0a0202;padding:12px 16px;'
                'margin-bottom:12px;animation:bossGlow 2s infinite alternate;">'
                '<div style="color:#ff5555;font-size:10px;letter-spacing:4px;margin-bottom:4px;">☠  BOSS ENCOUNTER</div>'
                '<div style="color:#ff8888;font-size:16px;font-weight:bold;margin-bottom:8px;">{name}</div>'
                '<div style="height:8px;background:#1a0404;border:1px solid #3a1010;'
                'margin-bottom:4px;overflow:hidden;"><div style="height:100%;width:{pct}%;'
                'background:linear-gradient(90deg,#7f0000,#ff5555);transition:width 0.4s;"></div></div>'
                '<div style="color:#ff5555;font-size:11px;">{hp} / {max} HP</div>'
                '</div>'
            ).format(name=b_name, pct=b_pct, hp=b_hp, max=b_max)
        else:
            boss_panel = (
                '<div style="border:1px solid #4ade80;background:#030e05;padding:10px 16px;'
                'margin-bottom:12px;text-align:center;color:#4ade80;font-size:13px;'
                'letter-spacing:3px;">✅ {} DEFEATED</div>'
            ).format(b_name)

    # Advance button
    advance_btn = ""
    if room.get("cleared") and (idx + 1) < total_rooms:
        advance_btn = (
            '<button onclick="window.__sq_action(\'go deeper\')" '
            'style="width:100%;background:linear-gradient(90deg,#0a2a10,#0f3818);'
            'border:1px solid #4ade80;color:#4ade80;font-family:Courier New,monospace;'
            'font-size:13px;letter-spacing:4px;padding:12px;cursor:pointer;margin-bottom:12px;'
            'box-shadow:0 0 16px rgba(74,222,128,0.2);">▶  GO DEEPER  →</button>'
        )

    # Victory screen
    victory_overlay = ""
    if total_rooms > 0 and idx == total_rooms - 1 and room.get("cleared") and is_boss:
        victory_overlay = (
            '<div style="position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9998;'
            'display:flex;flex-direction:column;align-items:center;justify-content:center;'
            'font-family:Courier New,monospace;text-align:center;">'
            '<div style="color:#fbbf24;font-size:32px;letter-spacing:8px;margin-bottom:16px;'
            'text-shadow:0 0 30px rgba(251,191,36,0.8);">★ DUNGEON CLEARED ★</div>'
            '<div style="color:#4ade80;font-size:14px;letter-spacing:3px;margin-bottom:24px;">'
            'You defeated {boss_name} and conquered every room.</div>'
            '<div style="color:#a0c4a8;font-size:12px;margin-bottom:24px;">'
            'Final Level: {level}  ·  Total XP: {xp}  ·  Items collected: {n_items}</div>'
            '<button onclick="document.getElementById(\'victory-overlay\').style.display=\'none\'" '
            'style="background:#0a1a0a;border:1px solid #4ade80;color:#4ade80;'
            'font-family:Courier New,monospace;font-size:13px;letter-spacing:4px;'
            'padding:12px 32px;cursor:pointer;">VIEW DUNGEON</button>'
            '</div>'
        ).format(
            boss_name=_h.escape(boss.get("name", "the boss")) if boss else "the boss",
            level=level, xp=xp, n_items=len(state.get("inventory", [])),
        )
        victory_overlay = victory_overlay.replace('id="victory-overlay"', '', 1)
        victory_overlay = victory_overlay.replace(
            '<div style="position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9998;',
            '<div id="victory-overlay" style="position:fixed;inset:0;background:rgba(0,0,0,0.9);z-index:9998;',
            1,
        )

    loot_html = _loot_popup_html(loot_items) if loot_items else ""
    inv_html = _inv_html(state.get("inventory", []))

    class_stats_html = "".join(
        '<div style="background:#020705;padding:6px 4px;text-align:center;border:1px solid #1a2a1a;">'
        '<div style="color:{accent};font-size:14px;font-weight:bold;">{v}</div>'
        '<div style="color:#2a4a2a;font-size:9px;">{k}</div></div>'.format(accent=cd["accent"], v=v, k=k)
        for k, v in cd["stats"].items()
    )

    atmosphere = room.get("atmosphere") or room.get("scene_description") or "The dungeon holds its breath..."

    return BASE_CSS + JS_BRIDGE + """
<style>
@keyframes scanline2 { 0% { background-position: 0 0; } 100% { background-position: 0 4px; } }
</style>
""" + loot_html + victory_overlay + """
<div class="sq-app" style="display:flex;flex-direction:column;">

  <!-- TOP HUD -->
  <div style="background:#040d06;border-bottom:1px solid #1a2a1a;padding:10px 16px;
    display:grid;grid-template-columns:auto 1fr auto auto auto;gap:16px;align-items:center;">
    <div style="color:#4ade80;font-size:16px;font-weight:900;letter-spacing:4px;
      text-shadow:0 0 12px rgba(74,222,128,0.6);">⚔ SNAPQUEST</div>
    <div style="display:flex;align-items:center;gap:0;">""" + map_slots + """</div>
    <div style="text-align:center;">
      <div style="color:""" + diff_color + """;font-size:9px;letter-spacing:3px;">""" + diff + """</div>
      <div style="color:#4a6a4a;font-size:10px;">ROOM """ + str(idx+1) + """/""" + str(total_rooms) + """</div>
    </div>
    <div style="min-width:140px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
        <span style="color:#ff5555;font-size:10px;letter-spacing:2px;">HP</span>
        <span style="color:""" + hp_color + """;font-size:10px;">""" + str(hp) + """/""" + str(max_hp) + """</span>
      </div>
      <div style="height:6px;background:#1a0404;border:1px solid #3a1010;">
        <div style="height:100%;width:""" + str(hp_pct) + """%;background:""" + hp_color + """;transition:width 0.4s;"></div>
      </div>
    </div>
    <div style="min-width:100px;text-align:right;">
      <div style="color:#fbbf24;font-size:10px;letter-spacing:2px;">LVL """ + str(level) + """</div>
      <div style="color:#4a6a4a;font-size:10px;">""" + str(xp % 100) + """/100 XP</div>
    </div>
  </div>

  <!-- MAIN CONTENT -->
  <div style="flex:1;display:grid;grid-template-columns:260px 1fr 240px;gap:0;min-height:600px;">

    <!-- LEFT: Class + Inventory -->
    <div style="border-right:1px solid #1a2a1a;background:#030806;display:flex;flex-direction:column;overflow:hidden;">
      <div style="border-bottom:1px solid #1a2a1a;padding:14px;">
        <div style="text-align:center;margin-bottom:10px;">
          <div style="font-size:28px;">""" + cd["icon"] + """</div>
          <div style="color:""" + cd["color"] + """;font-size:13px;font-weight:bold;letter-spacing:3px;">""" + cls.upper() + """</div>
          <div style="color:""" + cd["accent"] + """;font-size:10px;opacity:0.7;">""" + _h.escape(cd["tagline"]) + """</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">""" + class_stats_html + """</div>
      </div>
      <div style="flex:1;overflow-y:auto;padding:12px;">
        <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:10px;">INVENTORY</div>
        """ + inv_html + """
      </div>
    </div>

    <!-- CENTER: Scene + Chronicle -->
    <div style="display:flex;flex-direction:column;overflow:hidden;">
      <div style="border-bottom:1px solid #1a2a1a;padding:10px 16px;background:#040d06;
        display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="color:#1e3d28;font-size:10px;letter-spacing:3px;">LOCATION · </span>
          <span style="color:#a0c4a8;font-size:13px;letter-spacing:2px;">""" + _h.escape(scene_name) + """</span>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">""" + monster_html + """</div>
      </div>

      """ + boss_panel + """

      <div style="flex:1;overflow-y:auto;padding:16px;background:#030806;
        background-image:repeating-linear-gradient(0deg,transparent,transparent 3px,
          rgba(74,222,128,0.008) 3px,rgba(74,222,128,0.008) 4px);max-height:420px;">
        """ + story_lines + """
      </div>

      <div style="border-top:1px solid #1a2a1a;padding:12px 16px;background:#040d06;">
        """ + advance_btn + """
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
          """ + choice_btns + """
        </div>
        <div style="display:flex;gap:8px;">
          <input id="sq-custom-input" type="text"
            placeholder='Custom action — "attack", "search", "use ember flask"...'
            style="flex:1;background:#030806;border:1px solid #1a3a1a;color:#a0c4a8;
              font-family:Courier New,monospace;font-size:12px;padding:10px 12px;"
            onkeydown="if(event.key==='Enter'){window.__sq_action(this.value);}">
          <button onclick="window.__sq_action(document.getElementById('sq-custom-input').value)"
            style="background:#040d06;border:1px solid #2a5a2a;color:#4ade80;
              font-family:Courier New,monospace;font-size:12px;letter-spacing:2px;
              padding:10px 16px;cursor:pointer;">⚔ ACT</button>
        </div>
      </div>
    </div>

    <!-- RIGHT: Atmosphere -->
    <div style="border-left:1px solid #1a2a1a;background:#030806;display:flex;flex-direction:column;overflow:hidden;">
      <div style="padding:14px;flex:1;overflow-y:auto;">
        <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:10px;">ATMOSPHERE</div>
        <div style="color:#2a5a38;font-size:12px;line-height:1.8;font-style:italic;">""" + _h.escape(atmosphere) + """</div>
        <div style="margin-top:12px;border-top:1px solid #1a2a1a;padding-top:10px;">
          <div style="color:#1e3d28;font-size:10px;letter-spacing:2px;margin-bottom:6px;">ROOM STATUS</div>
          <div style="color:#1a3020;font-size:11px;line-height:1.7;">
            Difficulty: <span style="color:""" + diff_color + """;">""" + diff + """</span><br>
            Enemies: """ + ("Active" if room.get("enemy_alive") else "Defeated") + """<br>
            Room: """ + str(idx+1) + """ of """ + str(total_rooms) + """
          </div>
        </div>
      </div>
      <div style="padding:14px;border-top:1px solid #1a2a1a;">
        <div style="color:#1e3d28;font-size:10px;letter-spacing:3px;margin-bottom:10px;">VOICE COMMAND</div>
        <div id="sq-voice-mount"></div>
      </div>
    </div>
  </div>
</div>"""


# ════════════════════════════════════════════════════════════════════════════
# LOADING / ERROR helper
# ════════════════════════════════════════════════════════════════════════════

def loading_html(message: str) -> str:
    return BASE_CSS + JS_BRIDGE + """
<div class="sq-app" style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
  <div style="text-align:center;">
    <div style="color:#4ade80;font-size:24px;letter-spacing:6px;margin-bottom:16px;
      animation:loadingPulse 1.2s infinite;">⚔ LOADING</div>
    <div style="color:#2a5a38;font-size:12px;letter-spacing:2px;">""" + _h.escape(message) + """</div>
  </div>
</div>"""


def error_html(message: str) -> str:
    return BASE_CSS + JS_BRIDGE + """
<div class="sq-app" style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
  <div style="text-align:center;max-width:500px;padding:20px;">
    <div style="color:#ff5555;font-size:18px;letter-spacing:4px;margin-bottom:16px;">⚠ ERROR</div>
    <div style="color:#a0c4a8;font-size:12px;line-height:1.8;">""" + _h.escape(message) + """</div>
    <button onclick="window.__sq_go_back('s1')" style="margin-top:20px;background:#040d06;
      border:1px solid #2a5a2a;color:#4ade80;font-family:Courier New,monospace;
      font-size:12px;letter-spacing:2px;padding:10px 24px;cursor:pointer;">← BACK TO START</button>
  </div>
</div>"""