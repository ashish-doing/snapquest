"""
voice.py — ChronoQuest Audio I/O
STT : microphone .wav/.mp3 file -> faster-whisper (small) -> text
TTS : text -> edge-tts (en-GB-RyanNeural) -> .mp3 file path
"""

import asyncio
import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# STT
# ---------------------------------------------------------------------------

def transcribe_audio(audio_path: str) -> str:
    if not audio_path or not os.path.isfile(audio_path):
        logger.warning("transcribe_audio: invalid or missing path: %r", audio_path)
        return ""

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(audio_path, beam_size=5)
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text
    except ImportError:
        logger.debug("faster-whisper not installed, trying openai-whisper...")
    except Exception as exc:
        logger.error("faster-whisper failed: %s", exc)

    try:
        import whisper
        model = whisper.load_model("small")
        result = model.transcribe(audio_path)
        return result.get("text", "").strip()
    except ImportError:
        logger.error("No Whisper library found. pip install faster-whisper")
    except Exception as exc:
        logger.error("openai-whisper failed: %s", exc)

    return ""

# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

_ASCII_ART_RE = re.compile(
    r"[╔╗╚╝║═╠╣╦╩╬┌┐└┘│─├┤┬┴┼▓▒░█▄▀■□▪▫◆◇●○►◄★☆✦✧✨⚔️🗡️🏰⚡🌿💀]{2,}"
)
_MARKDOWN_RE = re.compile(r"[*_`#>|\\]")
_MULTI_SPACE_RE = re.compile(r"\s{2,}")

def clean_for_speech(dm_response: dict) -> str:
    scene = str(dm_response.get("scene", "")).strip()
    story = str(dm_response.get("story", "")).strip()
    combined = f"{scene}  {story}".strip() if scene else story
    combined = _ASCII_ART_RE.sub(" ", combined)
    combined = _MARKDOWN_RE.sub("", combined)
    combined = _MULTI_SPACE_RE.sub(" ", combined).strip()
    words = combined.split()
    if len(words) > 100:
        combined = " ".join(words[:100]) + "..."
    return combined

# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

async def speak_async(text: str, output_path: str = None) -> str:
    if output_path is None:
        import tempfile, os
        output_path = os.path.join(tempfile.gettempdir(), "dm_voice.mp3")
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("edge-tts not installed. pip install edge-tts") from exc

    if not text or not text.strip():
        return output_path

    communicate = edge_tts.Communicate(text=text, voice="en-GB-RyanNeural")
    await communicate.save(output_path)
    return output_path

def speak(text: str, output_path: str = None) -> str:
    if output_path is None:
        import tempfile, os
        output_path = os.path.join(tempfile.gettempdir(), "dm_voice.mp3")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, speak_async(text, output_path))
                return future.result()
        else:
            return loop.run_until_complete(speak_async(text, output_path))
    except RuntimeError:
        return asyncio.run(speak_async(text, output_path))

# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    out = speak("Welcome to ChronoQuest. The dungeon awaits.")
    if os.path.isfile(out):
        size_kb = os.path.getsize(out) / 1024
        print(f"TTS OK -> {out} ({size_kb:.1f} KB)")
    else:
        print(f"TTS FAILED")
        sys.exit(1)
    fake = {"scene": "A dark corridor.", "story": "You move forward.", "choices": []}
    print(f"clean_for_speech: {clean_for_speech(fake)!r}")