---
title: SnapQuest
emoji: 📸
colorFrom: purple
colorTo: red
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: true
tags:
  - game
  - rpg
  - minicpm
  - vision
  - voice
  - hackathon
  - photo-to-rpg
  - modal
---

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Orbitron&weight=900&size=32&duration=3000&pause=1000&color=A855F7&center=true&vCenter=true&width=900&lines=SnapQuest+%E2%80%94+Your+Room+is+a+Dungeon;Photo+%E2%86%92+RPG+in+30+Seconds;MiniCPM-V+4.6+%C3%97+Modal+A10G+GPU" alt="SnapQuest" />

<br/>

<p>
  <a href="https://huggingface.co/build-small-hackathon"><img src="https://img.shields.io/badge/HF%20Build%20Small-Hackathon%202026-FF9D00?style=for-the-badge&logo=huggingface&logoColor=white" /></a>
  <a href="https://huggingface.co/openbmb/MiniCPM-V-4"><img src="https://img.shields.io/badge/MiniCPM--V%204.6-1.3B%20Params-7C3AED?style=for-the-badge" /></a>
  <a href="https://modal.com"><img src="https://img.shields.io/badge/Modal-A10G%20GPU-6D28D9?style=for-the-badge" /></a>
  <a href="https://gradio.app"><img src="https://img.shields.io/badge/Gradio-5.x-FF6B6B?style=for-the-badge" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Voice-Whisper%20+%20edge--tts-22C55E?style=for-the-badge" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white" /></a>
</p>

<br/>

> **HuggingFace Build Small Hackathon 2026 — Track: Adventure in Thousand Token Wood 🍄**  
> Upload any real photo. MiniCPM-V 4.6 reads it. Your bookshelf becomes the Archive of Ancient Tomes. Your lamp becomes the Flickering Oracle. A dungeon dungeon master builds your adventure from what it actually sees — not from a template.

<p>
  <a href="https://huggingface.co/spaces/ashish-doing/snapquest"><img src="https://img.shields.io/badge/%F0%9F%9A%80%20Play%20Live-HuggingFace%20Spaces-FF9D00?style=for-the-badge" /></a>
  <a href="https://ashish-doing.github.io/snapquest"><img src="https://img.shields.io/badge/%F0%9F%8C%90%20Landing%20Page-GitHub%20Pages-A855F7?style=for-the-badge" /></a>
  <a href="#demo-video"><img src="https://img.shields.io/badge/%F0%9F%8E%AC%20Demo%20Video-YouTube-FF0000?style=for-the-badge&logo=youtube" /></a>
</p>

</div>

---

## What SnapQuest Does

You upload a photo of your room. SnapQuest turns it into a dungeon you can actually play.

Not a generic dungeon. **Your** dungeon. The one built from your chair, your curtain, your backpack, your desk lamp — transformed by a 1.3B vision model that reads the image directly.

```
📸 Your photo  →  👁️ MiniCPM-V 4.6 sees it  →  🗺️ Dungeon built from real objects  →  ⚔️ You play it
```

| Real Object | Becomes |
|---|---|
| Bookshelf | Archive of Ancient Tomes |
| Desk lamp | Flickering Oracle |
| Chair | Throne of the Forgotten Scholar |
| Curtain | Veil of Shadow |
| Backpack | Pack of the Wandering Rogue |

Pick your class. The Dungeon Master speaks differently depending on who you are. A Rogue sees shadows others walk past. A Mage sees arcane signatures in every object. A Healer notices what needs protecting.

---

## Why This is Different

Most AI RPGs use templates. You pick a setting ("dungeon", "forest", "city") and get a pre-written adventure with your name swapped in.

SnapQuest does something no other submission does: **it reads your actual photo**.

MiniCPM-V 4.6 — 1.3 billion parameters — runs on Modal's A10G GPU. It sees your specific room. Identifies your specific objects. Builds a scene grounded in what it actually observed. Every playthrough is unrepeatable because every photo is different.

---

## Prize Track Targets

| Track | Why SnapQuest Qualifies |
|---|---|
| **OpenBMB $10k** | Core model is MiniCPM-V 4.6 doing real multimodal vision on real uploaded photos — not text-only, not a wrapper |
| **Main Prize $15k** | Adventure in Thousand Token Wood — creative, delightful, AI-is-the-core experience |
| **OpenAI Codex** | Repo contains Codex-attributed commits; Codex used as coding agent during development |

---

## Architecture

```
User uploads photo
        │
        ▼
┌───────────────────────┐
│     vision.py         │
│  Base64 encode image  │
│  POST to Modal HTTPS  │
│  3x retry w/ backoff  │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────────────────────┐
│         Modal A10G GPU                │
│         modal_app.py                  │
│                                       │
│   MiniCPM-V 4.6 (1.3B params)        │
│   Reads actual image pixels           │
│   Returns structured JSON:            │
│   {scene_name, objects[], atmosphere, │
│    dm_intro, room_type, lighting}     │
└──────────┬────────────────────────────┘
           │
           ▼
┌───────────────────────┐
│    engine_photo.py    │
│  Photo-aware state    │
│  qwen2.5vl:3b DM      │
│  Class-specific voice │
│  Turn tracking        │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐     ┌─────────────────────┐
│     ui_photo.py       │     │      voice.py        │
│  Gradio 5.x           │◄────│  Whisper STT         │
│  CRT RPG interface    │     │  edge-tts TTS        │
│  Chronicle feed       │     │  en-GB-RyanNeural    │
│  HP + Inventory       │     └─────────────────────┘
│  Class picker         │
└───────────────────────┘
```

---

## Five Playable Classes

Each class changes how the Dungeon Master narrates your world:

| Class | Lens |
|---|---|
| ⚔️ **Swordsman** | Threat assessment, cover, weapons — sees your room as a battlefield |
| 🏹 **Archer** | Vantage points, escape routes, distances — your ceiling fan is a threat |
| 💚 **Healer** | Vulnerability, protection, what needs saving — warm and watchful |
| 🗡️ **Rogue** | Shadows, hiding spots, things worth stealing — sees what others miss |
| 🔮 **Mage** | Arcane signatures, omens, symbolic meaning — everything hums with power |

---

## Voice I/O

- **Input:** Whisper (local, free) — click mic, speak your action, it transcribes
- **Output:** edge-tts with `en-GB-RyanNeural` — the DM speaks every response aloud
- **No API key needed** — both run fully local

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Vision | MiniCPM-V 4.6 (OpenBMB) | Reads real photos, extracts scene JSON |
| GPU Infra | Modal A10G | Runs the 1.3B model on demand |
| Game Engine | qwen2.5vl:3b via Ollama | DM narrative generation |
| Voice In | OpenAI Whisper (local) | Speech-to-text |
| Voice Out | edge-tts RyanNeural | Text-to-speech |
| UI | Gradio 5.x | CRT-style RPG interface |
| Retry Logic | Custom exponential backoff | 3 retries, 1s/2s/4s delays |
| Deployment | HuggingFace Spaces | Public live demo |

---

## Project Structure

```
snapquest/
├── app.py              # Entry point: launches Gradio UI
├── modal_app.py        # Modal GPU deployment of MiniCPM-V 4.6
├── vision.py           # Calls Modal endpoint, parses scene JSON, retry logic
├── engine_photo.py     # Game state, DM generation, class perspectives
├── ui_photo.py         # Full Gradio UI: onboarding, classes, chronicle, voice
├── voice.py            # Whisper STT + edge-tts TTS pipeline
├── requirements.txt    # Dependencies
└── snapquest_landing.html  # Standalone landing page
```

---

## Run Locally

```bash
git clone https://github.com/ashish-doing/snapquest
cd snapquest
pip install -r requirements.txt

# Install and start Ollama with DM model
ollama pull qwen2.5vl:3b

# Set Modal endpoint
export SNAPQUEST_MODAL_ENDPOINT=https://ashish-kumar-doing--snapquest-minicpm-v-46-minicpmvservi-12daf4.modal.run

python app.py
# → http://localhost:7860
```

### HuggingFace Space Secrets
```
SNAPQUEST_MODAL_ENDPOINT  — Modal GPU endpoint URL
```

### Requirements
```
gradio>=5.9.1
requests
edge-tts
openai-whisper
Pillow
modal
```

---

## Badges Claimed

- 🍄 **Adventure in Thousand Token Wood** — creative, playful, AI-is-the-core
- 🔬 **OpenBMB Special Award** — MiniCPM-V 4.6 doing real vision on real photos
- 📓 **Field Notes** — "I built an RPG that reads your room"
- 🎙️ **Voice I/O** — Whisper + edge-tts fully integrated

---

## Demo Video

> Upload a photo of your room → pick Rogue → watch MiniCPM-V find your objects → play 3 turns → speak a custom action

*[Link added after recording]*

---

## Author

**Ashish Kumar** — B.Tech ECE, IIIT Guwahati

[![GitHub](https://img.shields.io/badge/GitHub-ashish--doing-181717?style=flat-square&logo=github)](https://github.com/ashish-doing)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-ashish--kumar-0A66C2?style=flat-square&logo=linkedin)](https://linkedin.com/in/ashish-kumar-014aaa3b9)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-ashish--doing-FF9D00?style=flat-square&logo=huggingface)](https://huggingface.co/ashish-doing)

---

<div align="center">

Built for **HuggingFace Build Small Hackathon 2026**

*Powered by MiniCPM-V 4.6 · Modal · Whisper · edge-tts · Gradio*

**Small model. Real vision. Your world becomes the dungeon.**

</div>