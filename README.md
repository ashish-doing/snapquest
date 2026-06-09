---
title: ChronoQuest
emoji: ⚔️
colorFrom: red
colorTo: gray
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: true
tags:
  - game
  - rpg
  - minicpm
  - local-model
  - voice
  - hackathon
---

# ⚔ ChronoQuest

**An entire RPG dungeon master. 1.3 billion parameters. Your laptop.**

Built for the [Build Small Hackathon](https://huggingface.co/build-small-hackathon) — Track: Thousand Token Wood 🍄

## What it does
- Voice or text input → AI Dungeon Master continues your story
- ASCII art scene renders every turn
- Full game state: HP, inventory, quest log
- Runs on MiniCPM-V 4.6 (1.3B params) via Ollama — no cloud API

## Badges claimed
- 🔌 Off the Grid — fully local, zero cloud
- 🦙 Llama Champion — MiniCPM-V 4.6 GGUF via Ollama
- 🎨 Off-Brand — custom CRT RPG Gradio UI
- 📓 Field Notes — [blog post link]

## Run locally
```bash
ollama pull openbmb/minicpm-v4.6
pip install -r requirements.txt
python app.py
```