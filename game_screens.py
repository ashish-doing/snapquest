"""game_screens.py — SnapQuest rich RPG UI.

Design direction:
  - Palette: deep obsidian (#08090d), blood-parchment (#1a0f08), gold (#c9a84c),
    arcane-teal (#3aafa9), crimson (#cc2936), ghost-white (#e8e4d9)
  - Font: MedievalSharp for display, Cinzel for headers, system-mono for HUD data
  - Aesthetic: illuminated manuscript meets terminal dungeon — not Gradio, not generic dark-green
  - Signature: animated rune border that pulses on boss encounters
  - JS bridge is embedded directly in every screen (no head= needed)
"""
from __future__ import annotations
import html as _h
import json
from game_data import CHARACTER_CLASSES, CLASS_DATA, LOOT_TIERS

# ══════════════════════════════════════════════════════════════════════════════
# JS BRIDGE — embedded in every screen so head= is NOT required
# ══════════════════════════════════════════════════════════════════════════════

JS_BRIDGE = """
<script>
(function() {
  function findEls() {
    return {
      box: document.querySelector('#sq-cmd-box textarea') ||
           document.querySelector('[id*="sq-cmd-box"] textarea'),
      btn: document.querySelector('#sq-cmd-btn button') ||
           document.querySelector('[id*="sq-cmd-btn"] button'),
    };
  }

  window.__sq_send = function(cmdObj) {
    var els = findEls();
    if (!els.box || !els.btn) {
      setTimeout(function(){ window.__sq_send(cmdObj); }, 150);
      return;
    }
    var s = JSON.stringify(cmdObj);
    var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setter.call(els.box, s);
    els.box.dispatchEvent(new Event('input', {bubbles:true}));
    setTimeout(function(){ els.btn.click(); }, 60);
  };

  window.__sq_action       = function(t){ if(t&&t.trim()) { window.__sq_send({cmd:'action',text:t}); var inp=document.getElementById('sq-custom-input'); if(inp) inp.value=''; } };
  window.__sq_goto_class   = function(){ window.__sq_send({cmd:'goto_class'}); };
  window.__sq_select_class = function(c){ window.__sq_send({cmd:'select_class',cls:c}); };
  window.__sq_start_dungeon= function(){ window.__sq_send({cmd:'start_dungeon'}); };
  window.__sq_go_back      = function(s){ window.__sq_send({cmd:'go_back',to:s}); };

  window.__sq_pick_file = function(slot) {
    var inp = document.getElementById('sq-file-'+slot);
    if(inp) inp.click();
  };
  window.__sq_handle_file = function(slot, inp) {
    if(!inp.files||!inp.files[0]) return;
    var r = new FileReader();
    r.onload = function(e){ window.__sq_send({cmd:'upload',slot:slot,data:e.target.result,name:inp.files[0].name}); };
    r.readAsDataURL(inp.files[0]);
  };
})();
</script>
"""

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL STYLES  — medieval-RPG, no generic dark-green CRT
# ══════════════════════════════════════════════════════════════════════════════

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;900&family=Cinzel+Decorative:wght@400;700&family=IM+Fell+English:ital@0;1&family=Share+Tech+Mono&display=swap');

:root {
  --obsidian:   #08090d;
  --parchment:  #1a1108;
  --gold:       #c9a84c;
  --gold-dim:   #6b5520;
  --gold-bright:#f0d060;
  --teal:       #3aafa9;
  --teal-dim:   #1a4a47;
  --crimson:    #cc2936;
  --crimson-dim:#4a0a0e;
  --ghost:      #e8e4d9;
  --muted:      #7a7060;
  --panel:      #0d0e14;
  --panel2:     #11120a;
  --border:     #2a2418;
  --border-gold:#3a2e14;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

.sq-root {
  font-family: 'Share Tech Mono', 'Courier New', monospace;
  background: var(--obsidian);
  color: var(--ghost);
  min-height: 100vh;
  overflow-x: hidden;
}

/* Typography */
.sq-title { font-family: 'Cinzel Decorative', serif; }
.sq-header { font-family: 'Cinzel', serif; letter-spacing: .1em; }
.sq-lore { font-family: 'IM Fell English', Georgia, serif; font-style: italic; }
.sq-mono { font-family: 'Share Tech Mono', monospace; }

/* Rune border — animated on boss */
@keyframes runeGlow {
  0%,100% { opacity:.4; box-shadow: inset 0 0 10px rgba(204,41,54,.1); }
  50%      { opacity:1;  box-shadow: inset 0 0 30px rgba(204,41,54,.35), 0 0 20px rgba(204,41,54,.2); }
}
@keyframes goldPulse {
  0%,100% { box-shadow: 0 0 8px rgba(201,168,76,.15); }
  50%      { box-shadow: 0 0 24px rgba(201,168,76,.45); }
}
@keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }
@keyframes scanH {
  0%   { background-position: 0 0; }
  100% { background-position: 0 4px; }
}
@keyframes shimmer {
  0%   { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes bossEntrance {
  0%   { transform:scale(.96); opacity:.3; }
  100% { transform:scale(1); opacity:1; }
}
@keyframes loading {
  0%,100% { opacity:.3; }
  50%      { opacity:1; }
}

/* Scanline overlay */
.sq-scan::after {
  content:''; position:absolute; inset:0; pointer-events:none;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px,
    rgba(201,168,76,.018) 2px, rgba(201,168,76,.018) 4px);
  animation: scanH 8s linear infinite;
}

/* Gold dividers */
.sq-divider {
  height:1px;
  background: linear-gradient(90deg, transparent, var(--gold-dim), var(--gold), var(--gold-dim), transparent);
  margin: 0;
}
.sq-divider-v {
  width:1px;
  background: linear-gradient(180deg, transparent, var(--gold-dim) 20%, var(--border-gold) 80%, transparent);
}

/* Buttons */
.sq-btn {
  font-family: 'Cinzel', serif; font-size: 13px; letter-spacing: .2em;
  padding: 14px 24px; cursor: pointer; border: 1px solid var(--gold-dim);
  color: var(--gold); background: linear-gradient(135deg, #120d04, #1c1508);
  text-transform: uppercase; transition: all .2s; position: relative;
  overflow: hidden;
}
.sq-btn::before {
  content:''; position:absolute; inset:0; opacity:0; transition:opacity .2s;
  background: linear-gradient(135deg, rgba(201,168,76,.08), rgba(201,168,76,.02));
}
.sq-btn:hover { border-color: var(--gold); color: var(--gold-bright); }
.sq-btn:hover::before { opacity:1; }
.sq-btn:active { transform:scale(.98); }

.sq-btn-full { width:100%; text-align:center; display:block; }

.sq-btn-disabled {
  font-family:'Cinzel',serif; font-size:13px; letter-spacing:.2em;
  padding:14px 24px; width:100%; border:1px solid #222; color:#333;
  background:#09090d; text-transform:uppercase; cursor:not-allowed;
  text-align:center;
}

.sq-btn-action {
  font-family:'Share Tech Mono',monospace; font-size:11px; padding:10px 8px;
  cursor:pointer; border:1px solid var(--border-gold); color:var(--muted);
  background:var(--panel2); text-align:left; transition:all .15s; width:100%;
  line-height:1.4;
}
.sq-btn-action:hover { border-color:var(--gold-dim); color:var(--ghost); background:#16130a; }

.sq-btn-boss-action {
  border-color: var(--crimson-dim); color: #aa4444;
}
.sq-btn-boss-action:hover { border-color:var(--crimson); color:#ff8888; background:#120408; }

/* Panels */
.sq-panel {
  background: var(--panel);
  border: 1px solid var(--border);
}
.sq-panel-gold {
  background: var(--panel2);
  border: 1px solid var(--border-gold);
}

/* Tags */
.sq-tag {
  display:inline-block; border:1px solid var(--border-gold);
  padding:2px 8px; font-size:10px; color:var(--gold-dim); letter-spacing:.1em;
  margin:2px;
}
.sq-tag-boss { border-color:var(--crimson-dim); color:var(--crimson); }
.sq-tag-clear { border-color:#1a3a1a; color:#4a7a4a; }

/* Upload slot */
.sq-slot {
  border:1px solid var(--border); background:var(--parchment);
  min-height:140px; display:flex; flex-direction:column;
  align-items:center; justify-content:center; cursor:pointer;
  transition: border-color .2s, box-shadow .2s; text-align:center;
  position:relative; padding:12px;
}
.sq-slot:hover { border-color: var(--gold-dim); box-shadow: 0 0 12px rgba(201,168,76,.1); }
.sq-slot.loaded { border-color:var(--teal-dim); align-items:flex-start; justify-content:flex-start; }
.sq-slot img { width:100%; height:72px; object-fit:cover; border:1px solid var(--border); margin-bottom:6px; }

/* Class card */
.sq-class-card {
  border:1px solid var(--border); background:var(--panel);
  padding:18px 14px; cursor:pointer; transition:all .2s;
  position:relative; overflow:hidden;
}
.sq-class-card::before {
  content:''; position:absolute; top:0; left:0; right:0; height:2px;
  opacity:0; transition:opacity .2s;
}
.sq-class-card:hover { border-color:var(--border-gold); }
.sq-class-card.selected { animation: goldPulse 3s ease-in-out infinite; }

/* HP bar */
.sq-bar-track {
  height:6px; background:#1a0a0a; border:1px solid #2a1414; overflow:hidden;
}
.sq-bar-fill { height:100%; transition:width .4s ease; }

/* Inventory item */
.sq-inv-item {
  display:flex; align-items:center; gap:8px;
  padding:5px 0; border-bottom:1px solid var(--border); font-size:11px;
}

/* Chronicle line types */
.chronicle-player { color: #7ab8f5; }
.chronicle-combat  { color: var(--crimson); font-weight:bold; }
.chronicle-loot    { color: var(--gold); }
.chronicle-victory { color: #6bcf7f; font-weight:bold; }
.chronicle-system  { color: var(--muted); }
.chronicle-dm      { color: var(--ghost); line-height:1.75; }
.chronicle-divider { color: #2a2418; }

/* Corner ornaments */
.sq-corner { position:absolute; width:16px; height:16px; }
.sq-corner.tl { top:0; left:0; border-top:2px solid var(--gold-dim); border-left:2px solid var(--gold-dim); }
.sq-corner.tr { top:0; right:0; border-top:2px solid var(--gold-dim); border-right:2px solid var(--gold-dim); }
.sq-corner.bl { bottom:0; left:0; border-bottom:2px solid var(--gold-dim); border-left:2px solid var(--gold-dim); }
.sq-corner.br { bottom:0; right:0; border-bottom:2px solid var(--gold-dim); border-right:2px solid var(--gold-dim); }

/* Loot popup */
.sq-loot-overlay {
  position:fixed; inset:0; background:rgba(4,3,6,.93);
  z-index:9999; display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  font-family:'Share Tech Mono',monospace; animation:fadeIn .3s ease;
}
.sq-loot-card {
  border:1px solid; background:var(--panel2);
  padding:14px 18px; min-width:130px; text-align:center;
}

/* Victory overlay */
.sq-victory-overlay {
  position:fixed; inset:0; background:rgba(4,3,6,.95);
  z-index:9998; display:flex; flex-direction:column;
  align-items:center; justify-content:center; text-align:center;
  animation:fadeIn .5s ease;
}

/* Responsive */
@media (max-width:900px) {
  .sq-game-grid { grid-template-columns:1fr !important; }
  .sq-sidebar-l, .sq-sidebar-r { display:none !important; }
  .sq-class-grid { grid-template-columns:1fr 1fr !important; }
  .sq-slot-grid  { grid-template-columns:1fr !important; }
}
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _corner_ornaments() -> str:
    return (
        '<div class="sq-corner tl"></div>'
        '<div class="sq-corner tr"></div>'
        '<div class="sq-corner bl"></div>'
        '<div class="sq-corner br"></div>'
    )


def _hp_bar(hp: int, max_hp: int) -> str:
    pct = max(0, min(100, int(hp / max(max_hp, 1) * 100)))
    if pct < 30:   color, label_color = '#cc2936', '#ff6070'
    elif pct < 60: color, label_color = '#c9841c', '#f0a030'
    else:           color, label_color = '#3aafa9', '#70d8d0'
    return (
        '<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
        '<span style="font-size:9px;letter-spacing:.15em;color:#5a4a3a;">VITALITY</span>'
        '<span style="font-size:10px;color:{lc};">{hp}/{max}</span>'
        '</div>'
        '<div class="sq-bar-track">'
        '<div class="sq-bar-fill" style="width:{pct}%;background:{c};"></div>'
        '</div>'
    ).format(hp=hp, max=max_hp, pct=pct, c=color, lc=label_color)


def _xp_bar(xp: int) -> str:
    level = 1 + xp // 100
    xp_in = xp % 100
    return (
        '<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
        '<span style="font-size:9px;letter-spacing:.15em;color:#5a4a3a;">EXPERIENCE</span>'
        '<span style="font-size:10px;color:var(--gold-dim);">LVL {l} · {x}/100</span>'
        '</div>'
        '<div class="sq-bar-track" style="border-color:#2a2010;">'
        '<div class="sq-bar-fill" style="width:{pct}%;background:linear-gradient(90deg,#6b5520,#c9a84c);"></div>'
        '</div>'
    ).format(l=level, x=xp_in, pct=xp_in)


def _minimap(rooms: list, idx: int) -> str:
    parts = []
    for i, r in enumerate(rooms):
        if i == idx:
            c, sym, bc = '#c9a84c', '▶', '2px solid #c9a84c'
        elif r.get('cleared'):
            c, sym, bc = '#3aafa9', '✓', '1px solid #3aafa9'
        elif r.get('is_boss'):
            c, sym, bc = '#cc2936', '☠', '1px dashed #cc2936'
        else:
            c, sym, bc = '#2a2418', str(i+1), '1px solid #2a2418'
        tip = _h.escape(r.get('scene_name', f'Room {i+1}'))
        parts.append(
            f'<div title="{tip}" style="width:24px;height:24px;border:{bc};color:{c};'
            f'display:flex;align-items:center;justify-content:center;font-size:11px;'
            f'background:var(--panel);">{sym}</div>'
        )
        if i < len(rooms) - 1:
            parts.append('<div style="width:10px;height:1px;background:#2a2418;align-self:center;"></div>')
    return ''.join(parts)


def _inv_html(inventory: list) -> str:
    if not inventory:
        return '<div class="sq-lore" style="color:var(--muted);font-size:12px;">Your satchel is empty.</div>'
    rows = ''
    for item in inventory:
        if isinstance(item, dict):
            td = LOOT_TIERS.get(item.get('tier', 'common'), LOOT_TIERS['common'])
            rows += (
                '<div class="sq-inv-item">'
                '<span style="font-size:15px;min-width:20px;">{icon}</span>'
                '<div style="flex:1;min-width:0;">'
                '<div style="color:{color};font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:{glow};">{name}</div>'
                '<div style="color:var(--muted);font-size:10px;">{stat}</div>'
                '</div>'
                '<div style="font-size:9px;color:{color};opacity:.6;letter-spacing:.05em;white-space:nowrap;">{label}</div>'
                '</div>'
            ).format(
                icon=item.get('icon','📦'), color=td['color'], glow=td['glow'],
                name=_h.escape(item.get('name','?')), stat=_h.escape(item.get('stat','')),
                label=td['label'],
            )
        else:
            rows += f'<div class="sq-inv-item" style="color:var(--muted);">· {_h.escape(str(item))}</div>'
    return rows


def _loot_popup_html(items: list) -> str:
    if not items:
        return ''
    cards = ''
    for item in items:
        td = LOOT_TIERS.get(item.get('tier','common'), LOOT_TIERS['common'])
        cards += (
            '<div class="sq-loot-card" style="border-color:{color};box-shadow:{glow};">'
            '<div style="font-size:32px;margin-bottom:8px;">{icon}</div>'
            '<div style="color:{color};font-size:9px;letter-spacing:.2em;margin-bottom:4px;">{label}</div>'
            '<div class="sq-header" style="color:var(--ghost);font-size:13px;margin-bottom:4px;">{name}</div>'
            '<div style="color:var(--muted);font-size:11px;">{stat}</div>'
            '</div>'
        ).format(
            color=td['color'], glow=td['glow'], icon=item.get('icon','📦'),
            label=td['label'], name=_h.escape(item.get('name','?')), stat=_h.escape(item.get('stat','')),
        )
    return (
        '<div class="sq-loot-overlay" id="sq-loot-popup">'
        '<div style="position:relative;padding:40px 20px;text-align:center;">'
        + _corner_ornaments() +
        '<div class="sq-title" style="color:var(--gold);font-size:22px;letter-spacing:.3em;'
        'margin-bottom:6px;text-shadow:0 0 20px rgba(201,168,76,.6);">✦ SPOILS OF BATTLE ✦</div>'
        '<div class="sq-lore" style="color:var(--muted);margin-bottom:28px;">The dungeon yields its secrets.</div>'
        '<div style="display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin-bottom:32px;">'
        + cards +
        '</div>'
        '<button onclick="document.getElementById(\'sq-loot-popup\').remove()" class="sq-btn">'
        'CLAIM YOUR SPOILS</button>'
        '</div></div>'
    )


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — LANDING / UPLOAD
# ══════════════════════════════════════════════════════════════════════════════

def screen1_html(photos: list, loading: bool = False) -> str:
    room_labels = ['ENTRY HALL', 'INNER CHAMBER', 'BOSS LAIR ☠']
    room_descs  = ['Required · 1st room', 'Optional · 2nd room', 'Optional · Final boss']
    slots_html  = ''

    for i in range(3):
        p    = photos[i] if i < len(photos) else {}
        has  = bool(p.get('path'))
        objs = p.get('objects', [])

        if has:
            tags = ''.join(f'<span class="sq-tag">{_h.escape(o)}</span>' for o in objs)
            boss_note = ''
            if i == 2 and objs:
                boss_note = (
                    '<div style="margin-top:8px;border:1px solid var(--crimson-dim);'
                    'padding:4px 8px;background:#0a0205;color:var(--crimson);'
                    'font-size:10px;letter-spacing:.15em;">☠ BOSS · {}</div>'
                ).format(_h.escape(objs[0].upper()))
            inner = (
                '<img src="{src}" style="width:100%;height:68px;object-fit:cover;border:1px solid var(--border);margin-bottom:6px;">'
                '<div style="color:var(--teal);font-size:9px;letter-spacing:.2em;margin-bottom:4px;">✓ ANALYZED</div>'
                '<div style="line-height:1.6;">{tags}</div>{boss}'
            ).format(src=p.get('path',''), tags=tags, boss=boss_note)
            extra_cls = ' loaded'
        else:
            rune = ['⚔', '🏰', '☠'][i]
            inner = (
                '<div style="font-size:28px;color:#2a2020;margin-bottom:8px;">{rune}</div>'
                '<div class="sq-header" style="color:#3a2e14;font-size:10px;letter-spacing:.2em;">{label}</div>'
                '<div style="color:#1e1a10;font-size:10px;margin-top:4px;">{desc}</div>'
            ).format(rune=rune, label=room_labels[i], desc=room_descs[i])
            extra_cls = ''

        slots_html += (
            '<div class="sq-slot{extra}" onclick="window.__sq_pick_file({i})" style="position:relative;">'
            + _corner_ornaments() +
            '<div style="position:absolute;top:6px;left:10px;font-size:9px;'
            'letter-spacing:.25em;color:#3a2e14;">{n}</div>'
            '<div style="margin-top:18px;width:100%;">{inner}</div>'
            '<input type="file" id="sq-file-{i}" accept="image/*" style="display:none"'
            ' onchange="window.__sq_handle_file({i},this)">'
            '</div>'
        ).format(extra=extra_cls, i=i, n=f'0{i+1} · {room_labels[i]}', inner=inner)

    n_loaded  = sum(1 for p in photos if p.get('path'))
    can_go    = n_loaded >= 1 and not loading
    label_map = {1:'1-room dungeon', 2:'2-room dungeon', 3:'3-room dungeon'}

    if loading:
        btn = (
            '<div class="sq-btn-disabled" style="animation:loading 1.2s infinite;font-size:12px;">'
            '⚗ MINICPM-V 4.6 READING YOUR WORLD...</div>'
        )
    elif can_go:
        btn = (
            '<button class="sq-btn sq-btn-full" onclick="window.__sq_goto_class()">'
            '⚔&nbsp;&nbsp;CHOOSE YOUR CLASS&nbsp;&nbsp;→</button>'
            '<div style="text-align:center;color:var(--gold-dim);font-size:10px;'
            'letter-spacing:.15em;margin-top:8px;">{} ready to be conquered</div>'
        ).format(label_map.get(n_loaded, ''))
    else:
        btn = '<div class="sq-btn-disabled">UPLOAD AT LEAST ONE PHOTO TO BEGIN</div>'

    return GLOBAL_CSS + JS_BRIDGE + """
<div class="sq-root">

  <!-- HERO -->
  <div class="sq-scan" style="position:relative;background:radial-gradient(ellipse at 50% 0%,#12090a 0%,var(--obsidian) 65%);
    border-bottom:1px solid var(--border-gold);padding:48px 24px 36px;text-align:center;overflow:hidden;">
    <!-- Decorative runes -->
    <div style="position:absolute;top:16px;left:24px;color:#1e1808;font-size:28px;opacity:.4;
      font-family:'Cinzel Decorative',serif;">ᚱ</div>
    <div style="position:absolute;top:16px;right:24px;color:#1e1808;font-size:28px;opacity:.4;
      font-family:'Cinzel Decorative',serif;">ᚦ</div>
    <div style="position:absolute;bottom:12px;left:40px;color:#1e1808;font-size:20px;opacity:.3;">ᛗ ᚢ ᛞ</div>
    <div style="position:absolute;bottom:12px;right:40px;color:#1e1808;font-size:20px;opacity:.3;">ᛁ ᚾ ᚺ</div>

    <div class="sq-title" style="font-size:52px;font-weight:700;letter-spacing:.18em;
      color:var(--gold);text-shadow:0 0 40px rgba(201,168,76,.5),0 2px 0 rgba(0,0,0,.8);
      margin-bottom:6px;line-height:1;">SNAPQUEST</div>
    <div class="sq-header" style="color:var(--gold-dim);font-size:11px;letter-spacing:.4em;
      margin-bottom:24px;">YOUR CHAMBER · YOUR DUNGEON · YOUR FATE</div>

    <div class="sq-divider" style="max-width:480px;margin:0 auto 20px;"></div>

    <div class="sq-lore" style="color:var(--muted);font-size:14px;line-height:1.8;
      max-width:520px;margin:0 auto 24px;">
      Photograph any real space. MiniCPM-V 4.6 reads every object within it.<br>
      Your <span style="color:var(--gold);font-style:normal;">bookshelf</span> becomes the Archive of Ancient Tomes.
      Your <span style="color:var(--crimson);font-style:normal;">lamp</span> becomes the final guardian.
    </div>

    <div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">
      <span class="sq-tag" style="border-color:var(--border-gold);color:var(--gold-dim);">1.3B PARAMS</span>
      <span class="sq-tag" style="border-color:var(--border-gold);color:var(--gold-dim);">MODAL A10G GPU</span>
      <span class="sq-tag" style="border-color:var(--border-gold);color:var(--gold-dim);">MULTI-ROOM</span>
      <span class="sq-tag sq-tag-boss">☠ BOSS FIGHTS</span>
      <span class="sq-tag" style="border-color:var(--teal-dim);color:var(--teal);">VOICE I/O</span>
    </div>
  </div>

  <!-- UPLOAD -->
  <div style="max-width:800px;margin:0 auto;padding:36px 24px;">

    <div class="sq-header" style="color:var(--gold-dim);font-size:10px;letter-spacing:.35em;
      margin-bottom:16px;">◈ UPLOAD YOUR CHAMBERS ( 1 REQUIRED · 3 FOR FULL DUNGEON )</div>

    <div class="sq-slot-grid" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px;">
""" + slots_html + """
    </div>

    <!-- How it works -->
    <div class="sq-panel-gold" style="padding:18px 20px;margin-bottom:24px;position:relative;">
""" + _corner_ornaments() + """
      <div class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.3em;margin-bottom:14px;">
        THE RITUAL OF SIGHT</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;text-align:center;">
        <div>
          <div style="font-size:26px;margin-bottom:8px;">📸</div>
          <div class="sq-lore" style="color:var(--muted);font-size:12px;line-height:1.6;">
            MiniCPM-V reads the objects within your photograph</div>
        </div>
        <div>
          <div style="font-size:26px;margin-bottom:8px;">⚗</div>
          <div class="sq-lore" style="color:var(--muted);font-size:12px;line-height:1.6;">
            Each object is transformed into a dungeon element or creature</div>
        </div>
        <div>
          <div style="font-size:26px;margin-bottom:8px;">☠</div>
          <div class="sq-lore" style="color:var(--crimson);font-size:12px;line-height:1.6;">
            The last photo's dominant object becomes your final guardian</div>
        </div>
      </div>
    </div>

""" + btn + """
  </div>
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — CLASS SELECTION
# ══════════════════════════════════════════════════════════════════════════════

# Per-class accent overrides that make each card feel different
_CLS_ACCENT = {
    'Swordsman': ('var(--teal)',    'var(--teal-dim)'),
    'Archer':    ('#c9a84c',        '#4a3a10'),
    'Healer':    ('#6bcf7f',        '#1a3a1a'),
    'Rogue':     ('#c084fc',        '#2a1a3a'),
    'Mage':      ('#60a5fa',        '#1a2a3a'),
}

def screen2_html(selected_class: str | None, dungeon_summary: str = '') -> str:
    cards = ''
    for cls in CHARACTER_CLASSES:
        d = CLASS_DATA[cls]
        acc, acc_dim = _CLS_ACCENT[cls]
        is_sel = cls == selected_class
        border = f'2px solid {acc}' if is_sel else '1px solid var(--border)'
        bg     = '#12100a' if is_sel else 'var(--panel)'
        badge  = (
            f'<div class="sq-header" style="color:{acc};font-size:9px;letter-spacing:.2em;'
            f'margin-top:10px;text-align:center;">✓ CHOSEN</div>'
        ) if is_sel else ''

        stats = ''.join(
            f'<div style="text-align:center;background:var(--parchment);padding:6px 4px;border:1px solid var(--border);">'
            f'<div class="sq-title" style="color:{acc};font-size:14px;">{v}</div>'
            f'<div style="color:#3a3020;font-size:9px;letter-spacing:.1em;">{k}</div></div>'
            for k, v in d['stats'].items()
        )
        perks = ''.join(
            f'<div style="color:var(--muted);font-size:11px;padding:4px 0;'
            f'border-bottom:1px solid var(--border);">▸ {_h.escape(p)}</div>'
            for p in d['perks']
        )

        cards += (
            f'<div class="sq-class-card{" selected" if is_sel else ""}" '
            f'onclick="window.__sq_select_class(\'{cls}\')" '
            f'style="border:{border};background:{bg};">'
            f'<div style="text-align:center;margin-bottom:14px;">'
            f'<div style="font-size:30px;">{d["icon"]}</div>'
            f'<div class="sq-header" style="color:{acc};font-size:13px;letter-spacing:.15em;margin-top:6px;">{cls.upper()}</div>'
            f'<div class="sq-lore" style="color:#5a5040;font-size:11px;margin-top:2px;">{_h.escape(d["tagline"])}</div>'
            f'</div>'
            f'<div class="sq-divider" style="margin-bottom:10px;"></div>'
            f'<div class="sq-lore" style="color:var(--muted);font-size:11px;line-height:1.7;margin-bottom:12px;">{_h.escape(d["desc"])}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:12px;">{stats}</div>'
            f'<div style="margin-bottom:10px;">{perks}</div>'
            f'<div style="border:1px solid var(--border);padding:6px 8px;'
            f'color:#3a3020;font-size:10px;font-style:italic;">"{_h.escape(d["playstyle"])}"</div>'
            f'{badge}'
            f'</div>'
        )

    btn = (
        '<button class="sq-btn sq-btn-full" onclick="window.__sq_start_dungeon()">⚔&nbsp;&nbsp;ENTER THE DUNGEON&nbsp;&nbsp;→</button>'
        if selected_class else
        '<div class="sq-btn-disabled">CHOOSE A CLASS BEFORE YOU DESCEND</div>'
    )

    summary_html = (
        f'<div class="sq-lore" style="text-align:center;color:var(--gold-dim);font-size:11px;margin-bottom:20px;">'
        f'{_h.escape(dungeon_summary)}</div>'
    ) if dungeon_summary else '<div style="margin-bottom:20px;"></div>'

    return GLOBAL_CSS + JS_BRIDGE + f"""
<div class="sq-root">
  <!-- TOPBAR -->
  <div style="background:var(--panel);border-bottom:1px solid var(--border-gold);
    padding:14px 24px;display:flex;align-items:center;justify-content:space-between;">
    <div class="sq-title" style="color:var(--gold);font-size:20px;letter-spacing:.15em;
      text-shadow:0 0 14px rgba(201,168,76,.5);">⚔ SNAPQUEST</div>
    <button onclick="window.__sq_go_back('s1')" class="sq-btn"
      style="padding:6px 16px;font-size:11px;">← BACK</button>
  </div>

  <div style="max-width:1100px;margin:0 auto;padding:28px 20px 48px;">
    <div style="text-align:center;margin-bottom:8px;">
      <div class="sq-title" style="color:var(--gold);font-size:22px;letter-spacing:.2em;
        margin-bottom:4px;">CHOOSE YOUR CLASS</div>
      <div class="sq-header" style="color:var(--gold-dim);font-size:10px;letter-spacing:.3em;">
        YOUR CHOICE SHAPES HOW THE DUNGEON REVEALS ITS SECRETS</div>
    </div>
    <div class="sq-divider" style="margin:16px auto;max-width:400px;"></div>
    {summary_html}
    <div class="sq-class-grid" style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:28px;">
      {cards}
    </div>
    {btn}
  </div>
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — DUNGEON COMBAT HUD
# ══════════════════════════════════════════════════════════════════════════════

def screen3_html(state: dict, story: str, loot_items: list | None = None) -> str:
    rooms     = state.get('rooms', [])
    idx       = state.get('room_index', 0)
    room      = rooms[min(idx, len(rooms)-1)] if rooms else {}
    total     = len(rooms)
    cls       = state.get('character_class', 'Swordsman')
    cd        = CLASS_DATA.get(cls, CLASS_DATA['Swordsman'])
    acc, _    = _CLS_ACCENT.get(cls, ('var(--teal)', 'var(--teal-dim)'))

    hp        = int(state.get('hp', 100))
    max_hp    = int(state.get('max_hp', 100))
    xp        = int(state.get('xp', 0))
    level     = 1 + xp // 100

    is_boss   = room.get('is_boss', False)
    boss      = room.get('boss') if is_boss else None
    boss_alive= boss.get('alive', True) if boss else False

    choices   = state.get('current_choices', ['Look around carefully', 'Move forward cautiously', 'Hold position and listen'])
    scene_name= room.get('scene_name', 'Unknown Realm')
    objects   = room.get('objects_found', [])
    diff      = room.get('difficulty', 'easy').upper()
    diff_c    = {'EASY':'var(--teal)', 'MEDIUM':'#c9841c', 'HARD':'var(--crimson)'}.get(diff, 'var(--teal)')

    atmosphere = room.get('atmosphere') or room.get('scene_description') or 'The dungeon watches. It waits.'

    # ── Chronicle ──
    chronicle_lines = ''
    for line in (story or '').split('\n'):
        esc = _h.escape(line)
        if not line.strip():
            chronicle_lines += '<div style="height:5px;"></div>'
        elif line.startswith('─') or line.startswith('═'):
            chronicle_lines += f'<div class="chronicle-divider">{esc}</div>'
        elif line.startswith('▷') or line.startswith('>'):
            chronicle_lines += f'<div class="chronicle-player">{esc}</div>'
        elif '⚔' in line or '💀' in line:
            chronicle_lines += f'<div class="chronicle-combat">{esc}</div>'
        elif '✅' in line or '🏆' in line:
            chronicle_lines += f'<div class="chronicle-victory">{esc}</div>'
        elif '💰' in line or '✨' in line:
            chronicle_lines += f'<div class="chronicle-loot">{esc}</div>'
        elif line.startswith('['):
            chronicle_lines += f'<div class="chronicle-system">{esc}</div>'
        else:
            chronicle_lines += f'<div class="chronicle-dm">{esc}</div>'

    # ── Choice buttons ──
    choice_btns = ''
    for i, c in enumerate(choices[:3]):
        btn_extra = ' sq-btn-boss-action' if (is_boss and boss_alive) else ''
        num = ['①', '②', '③'][i]
        choice_btns += (
            f'<button onclick="window.__sq_action({json.dumps(c)})" '
            f'class="sq-btn-action{btn_extra}">'
            f'<span style="color:var(--gold-dim);margin-right:8px;">{num}</span>'
            f'{_h.escape(c)}</button>'
        )

    # ── Monster tags ──
    monster_tags = ''
    for j, obj in enumerate(objects):
        if is_boss and j == 0 and boss:
            monster_tags += f'<span class="sq-tag sq-tag-boss">☠ {_h.escape(obj.upper())}</span>'
        else:
            monster_tags += f'<span class="sq-tag">{_h.escape(obj)}</span>'

    # ── Boss panel ──
    boss_panel = ''
    if is_boss and boss:
        b_hp  = boss.get('hp', 0)
        b_max = boss.get('max_hp', 100)
        b_pct = max(0, min(100, int(b_hp / max(b_max, 1) * 100)))
        b_name = _h.escape(boss.get('name', 'Unknown'))
        if boss_alive:
            boss_panel = (
                f'<div style="border:2px solid var(--crimson);background:#0a0208;'
                f'padding:12px 16px;margin-bottom:12px;position:relative;'
                f'animation:runeGlow 2s ease-in-out infinite;">'
                + _corner_ornaments() +
                f'<div style="color:var(--crimson);font-size:9px;letter-spacing:.3em;margin-bottom:4px;">☠ BOSS ENCOUNTER</div>'
                f'<div class="sq-header" style="color:#ff8888;font-size:15px;margin-bottom:8px;">{b_name}</div>'
                f'<div class="sq-bar-track" style="margin-bottom:4px;">'
                f'<div class="sq-bar-fill" style="width:{b_pct}%;background:linear-gradient(90deg,#4a0a0e,#cc2936);"></div>'
                f'</div>'
                f'<div style="color:var(--crimson);font-size:11px;">{b_hp} / {b_max} HP</div>'
                f'</div>'
            )
        else:
            boss_panel = (
                f'<div style="border:1px solid var(--teal-dim);background:#030e0a;'
                f'padding:10px 16px;margin-bottom:12px;text-align:center;">'
                f'<span class="sq-header" style="color:var(--teal);letter-spacing:.15em;">✓ {b_name} SLAIN</span>'
                f'</div>'
            )

    # ── Advance button ──
    advance_btn = ''
    if room.get('cleared') and (idx + 1) < total:
        advance_btn = (
            '<button onclick="window.__sq_action(\'go deeper\')" '
            'class="sq-btn sq-btn-full" style="margin-bottom:10px;animation:goldPulse 2s ease-in-out infinite;">'
            '▶&nbsp;&nbsp;DESCEND DEEPER&nbsp;&nbsp;→</button>'
        )

    # ── Victory overlay ──
    victory_overlay = ''
    if total > 0 and idx == total - 1 and room.get('cleared') and is_boss:
        b_name_v = _h.escape(boss.get('name', 'the guardian')) if boss else 'the guardian'
        victory_overlay = (
            f'<div id="sq-victory" class="sq-victory-overlay">'
            f'<div style="position:relative;padding:48px 32px;">'
            + _corner_ornaments() +
            f'<div class="sq-title" style="color:var(--gold);font-size:36px;letter-spacing:.2em;'
            f'margin-bottom:12px;text-shadow:0 0 40px rgba(201,168,76,.6);">★ DUNGEON CLEARED ★</div>'
            f'<div class="sq-divider" style="margin:0 auto 20px;max-width:360px;"></div>'
            f'<div class="sq-lore" style="color:var(--muted);font-size:14px;line-height:1.8;margin-bottom:24px;">'
            f'You have slain {b_name_v} and emerged victorious.<br>'
            f'The dungeon remembers your name.</div>'
            f'<div style="display:flex;gap:24px;justify-content:center;margin-bottom:32px;">'
            f'<div style="text-align:center;"><div class="sq-header" style="color:var(--gold);font-size:22px;">{level}</div>'
            f'<div style="color:var(--muted);font-size:10px;letter-spacing:.15em;">FINAL LEVEL</div></div>'
            f'<div style="text-align:center;"><div class="sq-header" style="color:var(--gold);font-size:22px;">{xp}</div>'
            f'<div style="color:var(--muted);font-size:10px;letter-spacing:.15em;">TOTAL XP</div></div>'
            f'<div style="text-align:center;"><div class="sq-header" style="color:var(--gold);font-size:22px;">{len(state.get("inventory",[]))}</div>'
            f'<div style="color:var(--muted);font-size:10px;letter-spacing:.15em;">ITEMS</div></div>'
            f'</div>'
            f'<button onclick="document.getElementById(\'sq-victory\').remove()" class="sq-btn">'
            f'VIEW THE AFTERMATH</button>'
            f'</div></div>'
        )

    loot_html = _loot_popup_html(loot_items) if loot_items else ''
    inv_html  = _inv_html(state.get('inventory', []))

    class_stats_html = ''.join(
        f'<div style="text-align:center;background:var(--parchment);padding:5px 4px;border:1px solid var(--border);">'
        f'<div class="sq-mono" style="color:{acc};font-size:13px;">{v}</div>'
        f'<div style="color:#3a2e14;font-size:9px;letter-spacing:.1em;">{k}</div></div>'
        for k, v in cd['stats'].items()
    )

    return GLOBAL_CSS + JS_BRIDGE + loot_html + victory_overlay + f"""
<div class="sq-root" style="display:flex;flex-direction:column;height:100vh;overflow:hidden;">

  <!-- TOP HUD BAR -->
  <div style="background:var(--panel);border-bottom:1px solid var(--border-gold);
    padding:8px 16px;display:grid;grid-template-columns:auto 1fr auto auto auto;
    gap:14px;align-items:center;flex-shrink:0;">

    <div class="sq-title" style="color:var(--gold);font-size:16px;letter-spacing:.15em;
      text-shadow:0 0 10px rgba(201,168,76,.4);">⚔ SQ</div>

    <!-- Minimap -->
    <div style="display:flex;align-items:center;gap:0;">{_minimap(rooms, idx)}</div>

    <!-- Difficulty + Room -->
    <div style="text-align:center;min-width:70px;">
      <div class="sq-header" style="color:{diff_c};font-size:9px;letter-spacing:.2em;">{diff}</div>
      <div style="color:var(--muted);font-size:10px;">ROOM {idx+1}/{total}</div>
    </div>

    <!-- HP -->
    <div style="min-width:150px;">{_hp_bar(hp, max_hp)}</div>

    <!-- XP -->
    <div style="min-width:120px;">{_xp_bar(xp)}</div>
  </div>

  <!-- MAIN 3-COLUMN GRID -->
  <div class="sq-game-grid" style="flex:1;display:grid;grid-template-columns:250px 1fr 220px;
    overflow:hidden;min-height:0;">

    <!-- ── LEFT: Class card + Inventory ── -->
    <div class="sq-sidebar-l" style="border-right:1px solid var(--border);background:var(--panel);
      display:flex;flex-direction:column;overflow:hidden;">

      <!-- Class card header -->
      <div style="padding:14px;border-bottom:1px solid var(--border-gold);flex-shrink:0;">
        <div style="text-align:center;margin-bottom:12px;">
          <div style="font-size:30px;">{cd["icon"]}</div>
          <div class="sq-header" style="color:{acc};font-size:12px;letter-spacing:.2em;margin-top:4px;">{cls.upper()}</div>
          <div class="sq-lore" style="color:var(--muted);font-size:10px;">{_h.escape(cd["tagline"])}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;">{class_stats_html}</div>
      </div>

      <!-- Inventory -->
      <div style="flex:1;overflow-y:auto;padding:12px;">
        <div class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.25em;margin-bottom:10px;">
          SATCHEL · {len(state.get("inventory",[]))} ITEMS</div>
        {inv_html}
      </div>
    </div>

    <!-- ── CENTER: Chronicle + Actions ── -->
    <div style="display:flex;flex-direction:column;overflow:hidden;min-width:0;">

      <!-- Scene header -->
      <div style="border-bottom:1px solid var(--border);padding:10px 16px;background:var(--parchment);
        flex-shrink:0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <div>
          <span class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.3em;">LOCATION · </span>
          <span class="sq-header" style="color:var(--ghost);font-size:13px;">{_h.escape(scene_name)}</span>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;">{monster_tags}</div>
      </div>

      {boss_panel}

      <!-- Chronicle feed -->
      <div style="flex:1;overflow-y:auto;padding:14px 16px;
        background:radial-gradient(ellipse at 50% 0%,#0e0c08 0%,var(--obsidian) 100%);
        font-size:12px;line-height:1.65;" id="sq-chronicle">
        {chronicle_lines}
      </div>

      <!-- Actions bar -->
      <div style="border-top:1px solid var(--border-gold);padding:12px 14px;
        background:var(--panel);flex-shrink:0;">
        {advance_btn}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px;">
          {choice_btns}
        </div>
        <div style="display:flex;gap:8px;">
          <input id="sq-custom-input" type="text"
            placeholder='Speak your action — "attack", "examine the lamp", "use scroll"...'
            style="flex:1;background:var(--parchment);border:1px solid var(--border-gold);
              color:var(--ghost);font-family:\'Share Tech Mono\',monospace;font-size:12px;
              padding:9px 12px;outline:none;"
            onkeydown="if(event.key==='Enter'){{ window.__sq_action(this.value); }}">
          <button onclick="window.__sq_action(document.getElementById('sq-custom-input').value)"
            class="sq-btn" style="padding:9px 14px;font-size:11px;white-space:nowrap;">
            ⚔ ACT</button>
        </div>
      </div>
    </div>

    <!-- ── RIGHT: Atmosphere + Status ── -->
    <div class="sq-sidebar-r" style="border-left:1px solid var(--border);background:var(--panel);
      display:flex;flex-direction:column;overflow:hidden;">
      <div style="flex:1;overflow-y:auto;padding:14px;">
        <div class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.25em;margin-bottom:10px;">
          ATMOSPHERE</div>
        <div class="sq-lore" style="color:var(--muted);font-size:12px;line-height:1.8;">
          {_h.escape(atmosphere)}</div>

        <div class="sq-divider" style="margin:14px 0;"></div>

        <div class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.25em;margin-bottom:8px;">
          ROOM STATUS</div>
        <div style="font-size:11px;line-height:1.9;color:var(--muted);">
          Difficulty:&nbsp;<span style="color:{diff_c};">{diff}</span><br>
          Enemies:&nbsp;<span style="color:{"var(--crimson)" if room.get("enemy_alive") else "var(--teal)"};">
            {"Active" if room.get("enemy_alive") else "Defeated"}</span><br>
          Room:&nbsp;{idx+1} of {total}
        </div>

        <div class="sq-divider" style="margin:14px 0;"></div>

        <div class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.25em;margin-bottom:8px;">
          CLASS PERKS</div>
        {''.join(f'<div style="color:var(--muted);font-size:10px;padding:3px 0;border-bottom:1px solid var(--border);">▸ {_h.escape(p)}</div>' for p in cd["perks"])}
      </div>

      <div style="padding:12px;border-top:1px solid var(--border);flex-shrink:0;">
        <div class="sq-header" style="color:var(--gold-dim);font-size:9px;letter-spacing:.2em;margin-bottom:8px;">
          VOICE COMMAND</div>
        <div id="sq-voice-mount" style="color:var(--muted);font-size:10px;">
          Use the mic widget below ↓</div>
      </div>
    </div>
  </div>
</div>
<script>
// Auto-scroll chronicle to bottom
(function() {{
  var el = document.getElementById('sq-chronicle');
  if(el) el.scrollTop = el.scrollHeight;
}})();
</script>"""


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY SCREENS
# ══════════════════════════════════════════════════════════════════════════════

def loading_html(message: str = 'Preparing your dungeon...') -> str:
    return GLOBAL_CSS + JS_BRIDGE + f"""
<div class="sq-root" style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
  <div style="text-align:center;position:relative;padding:40px;">
    {_corner_ornaments()}
    <div class="sq-title" style="color:var(--gold);font-size:28px;letter-spacing:.2em;
      margin-bottom:14px;animation:loading 1.2s ease-in-out infinite;">⚗ CONSULTING THE ORACLE</div>
    <div class="sq-lore" style="color:var(--muted);font-size:13px;">{_h.escape(message)}</div>
  </div>
</div>"""


def error_html(message: str) -> str:
    return GLOBAL_CSS + JS_BRIDGE + f"""
<div class="sq-root" style="display:flex;align-items:center;justify-content:center;min-height:100vh;">
  <div style="text-align:center;max-width:500px;padding:36px;position:relative;">
    {_corner_ornaments()}
    <div class="sq-title" style="color:var(--crimson);font-size:22px;letter-spacing:.15em;margin-bottom:14px;">
      ⚠ THE DUNGEON REJECTS YOU</div>
    <div class="sq-divider" style="margin:0 auto 20px;"></div>
    <div class="sq-lore" style="color:var(--muted);font-size:12px;line-height:1.8;margin-bottom:24px;">
      {_h.escape(message)}</div>
    <button onclick="window.__sq_go_back('s1')" class="sq-btn">← RETREAT TO SAFETY</button>
  </div>
</div>"""