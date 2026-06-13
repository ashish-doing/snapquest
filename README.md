---
title: SnapQuest
emoji: ⚔️
colorFrom: orange
colorTo: black
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: true
tags:
  - thousand-token-wood
  - off-brand
  - tiny-titan
  - best-demo
  - best-agent
  - openbmb
  - minicpm
  - game
  - rpg
  - voice
  - photo-to-rpg
  - modal
license: mit
---

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=900&size=32&duration=3000&pause=1000&color=8CFF9B&center=true&vCenter=true&width=900&lines=SnapQuest+%E2%80%94+Your+Room+is+a+Dungeon;1+Photo+%3D+1+Room+%7C+3+Photos+%3D+Full+Dungeon;Snap.+Fight.+Defeat+the+Boss." alt="SnapQuest" />

<br/>

<p>
  <a href="https://huggingface.co/build-small-hackathon"><img src="https://img.shields.io/badge/HF%20Build%20Small-Hackathon%202026-FF9D00?style=for-the-badge&logo=huggingface&logoColor=white" /></a>
  <a href="https://huggingface.co/openbmb/MiniCPM-V-4"><img src="https://img.shields.io/badge/MiniCPM--V%204.6-1.3B%20Params-7C3AED?style=for-the-badge" /></a>
  <a href="https://modal.com"><img src="https://img.shields.io/badge/Modal-A10G%20GPU-6D28D9?style=for-the-badge" /></a>
  <a href="https://gradio.app"><img src="https://img.shields.io/badge/Gradio-5.x-FF6B6B?style=for-the-badge" /></a>
</p>

> **Build Small Hackathon 2026 — Track: Thousand Token Wood 🍄**
> Upload any real photo. MiniCPM-V 4.6 reads it. Your room becomes a dungeon you can actually play.

**Demo Video:** [YouTube →](#) *(link added after recording)*
**Social Post:** [LinkedIn →](#) *(link added after posting)*

</div>

---

## What SnapQuest Does

Upload 1–3 photos of any real space. Each photo becomes one room of a dungeon. The last room always spawns a **boss** — an entity formed from the most prominent object the vision model detects.

```
📸 Photo 1  →  Room 1: Entry Hall
📸 Photo 2  →  Room 2: Inner Chamber  
📸 Photo 3  →  Room 3: BOSS LAIR ☠
```

MiniCPM-V 4.6 (1.3B parameters) reads each image directly. It sees your specific objects. It builds a scene grounded in what it actually observes — not a template.

| Real Object | Becomes |
|---|---|
| Red chair | Throne of the Forgotten Scholar |
| Black backpack | Wanderer's Cursed Pack |
| Stuffed bear | **☠ The Bear Sentinel — BOSS** |
| Desk lamp | Flickering Oracle |
| Curtain | Veil of Shadow |

---

## Five Classes, Five Worldviews

| Class | How They See Your Room |
|---|---|
| ⚔️ Swordsman | Cover, threats, chokepoints |
| 🏹 Archer | Vantage points, sightlines, escape routes |
| 💚 Healer | Vulnerability, what needs protecting |
| 🗡️ Rogue | Shadows, hiding spots, things worth stealing |
| 🔮 Mage | Arcane energy, omens, symbolic meaning |

---

## Game Loop

1. Upload 1–3 photos → pick class → **Begin Quest**
2. MiniCPM-V reads each photo, builds rooms
3. Click choices or type custom actions (try "attack the chair")
4. Combat: attack enemies to clear rooms, take damage in return
5. Type **"Go deeper"** to advance to the next room
6. Final room: **BOSS FIGHT** — the boss is built from your last photo's main object
7. Defeat the boss → dungeon cleared, loot collected

---

## Architecture

```
Photos (1–3)
    │
    ▼
vision.py  ─────────────────────────────────→  Modal A10G GPU
  Base64 encode + POST to Modal endpoint          MiniCPM-V 4.6 (1.3B)
  3x retry with backoff                          Returns: scene JSON per photo
    │
    ▼
dungeon.py
  build_rooms()  → 1–3 rooms with difficulty scaling
  generate_boss() → boss from photo's main object
  apply_combat()  → lightweight combat resolution
  minimap_html()  → pixel minimap display
    │
    ▼
engine_photo.py
  HF Inference API → Qwen2.5-3B-Instruct (free, serverless)
  Rule-based fallback (always works if HF is slow)
  Multi-room state management, history window
    │
    ▼
ui_photo.py  +  voice.py
  Gradio 5.x CRT interface        Whisper STT + edge-tts TTS
  Press Start 2P pixel font       en-GB-RyanNeural voice
  Boss banner + minimap + XP bar
```

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Vision | MiniCPM-V 4.6 (OpenBMB) | 1.3B params, reads real photos |
| GPU | Modal A10G | On-demand, scales to zero |
| DM Narration | Qwen2.5-3B-Instruct via HF Inference | Free serverless, no key needed |
| DM Fallback | Rule-based generator | Always playable even if API is slow |
| Voice In | OpenAI Whisper (local) | Speech → text |
| Voice Out | edge-tts RyanNeural | Text → speech |
| UI | Gradio 5.x + custom CSS | Press Start 2P font, CRT scanlines |
| Deployment | HuggingFace Spaces | Free tier |

---

## Run Locally

```bash
git clone https://github.com/ashish-doing/snapquest
cd snapquest
pip install -r requirements-local.txt

# Pull DM model locally (optional — HF Inference is used on Space)
ollama pull qwen2.5vl:3b

# Set Modal endpoint (get from: modal deploy modal_app.py)
export SNAPQUEST_MODAL_ENDPOINT=https://ashish-kumar-doing--snapquest-minicpm-v-46-minicpmvservi-12daf4.modal.run

python app.py
```

### HF Space Secrets Required
```
SNAPQUEST_MODAL_ENDPOINT  — Modal GPU endpoint URL
```

---

## Prize Tracks Targeted

| Prize | Qualification |
|---|---|
| 🍄 **Thousand Token Wood** ($4k) | Creative whimsical AI game — photo → dungeon |
| 🔬 **OpenBMB Best MiniCPM Build** ($2.5k) | MiniCPM-V 4.6 doing real multimodal vision |
| 🎨 **Off Brand Badge** ($1.5k) | Custom pixel UI, Press Start 2P font, boss banner, minimap |
| 🐜 **Tiny Titan Badge** ($1.5k) | Both models ≤4B: MiniCPM-V 1.3B + Qwen2.5 3B |
| 🎬 **Best Demo Badge** ($1k) | App + video + social post |
| 🤖 **Best Agent Badge** ($1k) | Multi-step: vision → room build → DM narration → combat |

---

## Author

**Ashish Kumar** — B.Tech ECE, IIIT Guwahati (Batch 2024)

[![GitHub](https://img.shields.io/badge/GitHub-ashish--doing-181717?style=flat-square&logo=github)](https://github.com/ashish-doing)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-ashish--doing-FF9D00?style=flat-square&logo=huggingface)](https://huggingface.co/ashish-doing)

---

<div align="center">

Built for **HuggingFace Build Small Hackathon 2026**

*MiniCPM-V 4.6 · Modal · Qwen2.5-3B · Whisper · edge-tts · Gradio*

**Small model. Real vision. Your room becomes the dungeon.**

</div>