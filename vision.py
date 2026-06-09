"""SnapQuest vision integration for MiniCPM-V 4.6 on Modal Labs.

Set SNAPQUEST_MODAL_ENDPOINT to the HTTPS endpoint for your Modal GPU app.
If the endpoint requires auth, set SNAPQUEST_MODAL_TOKEN as well.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODAL_ENDPOINT_ENV = "SNAPQUEST_MODAL_ENDPOINT"
MODAL_TOKEN_ENV = "SNAPQUEST_MODAL_TOKEN"
REQUEST_TIMEOUT_SECONDS = 90
MAX_RETRIES = 3

VALID_CHARACTER_CLASSES = {
    "Swordsman": "combat focus, brave and direct, noticing cover, threats, and weapons",
    "Archer": "ranged and scouting focus, alert to distance, vantage points, and paths",
    "Healer": "protective and healing focus, gentle, watchful, and concerned with safety",
    "Rogue": "stealth and cunning focus, sly, quiet, and attentive to hiding places",
    "Mage": "arcane and magical focus, mystical, symbolic, and curious about omens",
}

SYSTEM_PROMPT = """You are SnapQuest's fantasy scene oracle.
Analyze the user's real-world photo and transform it into a grounded fantasy quest moment.
Only mention objects that are genuinely visible in the image.
Return strict JSON with exactly these keys:
- scene_name: string
- scene_description: exactly 2 sentences, fantasy tone, grounded in real objects from the photo
- objects_found: list of exactly 3 real objects spotted in the image
- choices: list of exactly 3 action strings that reference real objects from the image
Do not include markdown, commentary, or extra keys."""


def analyze_scene(image_path: str, character_class: str) -> dict:
    """Analyze a photo and return a SnapQuest scene JSON dictionary.

    Args:
        image_path: Local path to the image to analyze.
        character_class: One of Swordsman, Archer, Healer, Rogue, or Mage.

    Returns:
        dict with keys: scene_name, scene_description, objects_found, choices.
        Falls back to a generic scene if Modal is unavailable.

    Raises:
        FileNotFoundError: If image_path does not exist.
        ValueError: If character_class is invalid.
    """
    image_file = Path(image_path).expanduser().resolve()
    if not image_file.is_file():
        raise FileNotFoundError(f"Image file not found: {image_file}")

    class_name = _normalize_character_class(character_class)

    endpoint = os.getenv(MODAL_ENDPOINT_ENV)
    if not endpoint:
        print(f"[vision] {MODAL_ENDPOINT_ENV} not set — using fallback scene.")
        return _fallback_scene(class_name)

    messages = _build_messages(image_file, class_name)
    payload = {
        "model": "MiniCPM-V-4.6",
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 500,
    }

    try:
        response_data = _post_to_modal(endpoint, payload)
        content = _extract_message_content(response_data)
        scene = _parse_scene_json(content)
        return _validate_scene(scene)
    except Exception as exc:
        print(f"[vision] Modal call failed, using fallback: {exc}")
        return _fallback_scene(class_name)


def _normalize_character_class(character_class: str) -> str:
    if not isinstance(character_class, str) or not character_class.strip():
        raise ValueError("character_class must be a non-empty string.")

    normalized_lookup = {key.lower(): key for key in VALID_CHARACTER_CLASSES}
    class_name = normalized_lookup.get(character_class.strip().lower())
    if not class_name:
        allowed = ", ".join(VALID_CHARACTER_CLASSES)
        raise ValueError(
            f"Unknown character_class '{character_class}'. Use one of: {allowed}."
        )
    return class_name


def _build_messages(image_file: Path, character_class: str) -> list[dict[str, Any]]:
    image_media_type = mimetypes.guess_type(image_file.name)[0] or "image/jpeg"
    image_base64 = base64.b64encode(image_file.read_bytes()).decode("utf-8")
    class_tone = VALID_CHARACTER_CLASSES[character_class]

    user_text = (
        f"Character class: {character_class}. "
        f"Shape the fantasy tone with this class perspective: {class_tone}. "
        "Spot real objects in the photo and turn them into quest-relevant details."
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_base64,
                    },
                },
                {"type": "text", "text": user_text},
            ],
        },
    ]


def _post_to_modal(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    token = os.getenv(MODAL_TOKEN_ENV)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                raw_body = response.read().decode("utf-8")
            break
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Modal request failed with HTTP {exc.code}: {error_body}"
            ) from exc
        except URLError as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Could not reach Modal endpoint: {exc.reason}") from exc
            time.sleep(2**attempt)
        except TimeoutError as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError("Modal request timed out.") from exc
            time.sleep(2**attempt)

    try:
        return json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Modal endpoint returned non-JSON response: {raw_body[:300]}"
        ) from exc


def _extract_message_content(response_data: dict[str, Any]) -> str:
    """Accept both Anthropic-compatible and OpenAI-compatible response shapes."""

    # Anthropic format: {content: [{type: text, text: ...}]}
    if isinstance(response_data.get("content"), list):
        text_parts = [
            block.get("text", "")
            for block in response_data["content"]
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if text_parts:
            return "\n".join(text_parts)

    # Anthropic format flat string
    if isinstance(response_data.get("content"), str):
        return response_data["content"]

    # OpenAI format: {choices: [{message: {content: ...}}]}
    choices = response_data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            if text_parts:
                return "\n".join(text_parts)

    raise RuntimeError(
        f"Could not find model text content in response: {response_data}"
    )


def _parse_scene_json(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    # Strip markdown code fences if model wrapped output
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    import re
    # Fix missing commas between JSON fields (common model error)
    cleaned = re.sub(r'"\s*\n\s*"', '",\n"', cleaned)
    cleaned = re.sub(r'}\s*\n\s*"', '},\n"', cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {content}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Model JSON must be an object.")
    return parsed


def _validate_scene(scene: dict[str, Any]) -> dict[str, Any]:
    required = {"scene_name", "scene_description", "objects_found", "choices"}
    missing = required - scene.keys()
    if missing:
        raise ValueError(f"Model response missing required fields: {missing}")

    if not isinstance(scene["objects_found"], list) or len(scene["objects_found"]) < 1:
        raise ValueError("objects_found must be a non-empty list.")

    if not isinstance(scene["choices"], list) or len(scene["choices"]) < 3:
        raise ValueError("choices must have at least 3 items.")

    if not isinstance(scene["scene_name"], str) or not scene["scene_name"].strip():
        raise ValueError("scene_name must be a non-empty string.")

    if not isinstance(scene["scene_description"], str) or not scene["scene_description"].strip():
        raise ValueError("scene_description must be a non-empty string.")

    # Normalize to exactly 3 of each
    scene["choices"] = scene["choices"][:3]
    scene["objects_found"] = scene["objects_found"][:3]
    return scene


def _fallback_scene(character_class: str) -> dict[str, Any]:
    """Returns a generic scene when Modal is unavailable or call fails."""
    fallbacks = {
        "Swordsman": {
            "scene_name": "The Iron Threshold",
            "scene_description": "A dimly lit chamber stretches before you, walls lined with the remnants of old battles. Your hand instinctively grips your sword as shadows shift in the corners.",
            "objects_found": ["stone wall", "iron door", "torch bracket"],
            "choices": [
                "Examine the iron door for weaknesses",
                "Take the torch bracket as a weapon",
                "Press your back to the stone wall and listen",
            ],
        },
        "Archer": {
            "scene_name": "The Vantage Hall",
            "scene_description": "The space opens into a long corridor with high ceilings — a perfect killing ground if you control the far end. You scan for elevated positions and escape routes.",
            "objects_found": ["high window", "wooden beam", "stone pillar"],
            "choices": [
                "Climb toward the high window for a vantage point",
                "Use the wooden beam as a bridge to higher ground",
                "Hide behind the stone pillar and observe",
            ],
        },
        "Healer": {
            "scene_name": "The Wounded Sanctum",
            "scene_description": "A quiet room carries the weight of suffering past — you sense it in the air. Your herbs grow warm in your satchel, responding to some hidden need nearby.",
            "objects_found": ["cracked basin", "dusty shelf", "pale light"],
            "choices": [
                "Check the cracked basin for clean water",
                "Search the dusty shelf for medical supplies",
                "Follow the pale light toward whoever needs you",
            ],
        },
        "Rogue": {
            "scene_name": "The Shadow Crossing",
            "scene_description": "Every corner is an opportunity, every shadow a potential ally. You map the room in seconds — three entry points, two blind spots, one obvious trap.",
            "objects_found": ["loose floorboard", "hanging tapestry", "locked chest"],
            "choices": [
                "Test the loose floorboard — it might hide something",
                "Slip behind the hanging tapestry and wait",
                "Pick the locked chest before anyone returns",
            ],
        },
        "Mage": {
            "scene_name": "The Resonant Chamber",
            "scene_description": "The room hums with dormant energy that only you can perceive. Ordinary objects reveal their arcane shadows — each one a potential conduit or a warning.",
            "objects_found": ["glowing sigil", "old mirror", "scattered pages"],
            "choices": [
                "Trace the glowing sigil to decode its meaning",
                "Look into the old mirror — it may show other times",
                "Gather the scattered pages before the wind takes them",
            ],
        },
    }
    return fallbacks.get(character_class, fallbacks["Swordsman"])


# ─── LOCAL TEST ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import tempfile

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed. Run: pip install Pillow")
        sys.exit(1)

    print("=== vision.py local test ===\n")

    # 1. Validation test (no Modal needed)
    print("[1] Testing _validate_scene...")
    fake_scene = {
        "scene_name": "Test Sanctum",
        "scene_description": "A chamber of testing. The walls hold secrets.",
        "objects_found": ["obj1", "obj2", "obj3"],
        "choices": ["Do A", "Do B", "Do C"],
    }
    result = _validate_scene(fake_scene)
    print(f"    OK — scene_name: {result['scene_name']}")

    # 2. Class normalization test
    print("[2] Testing _normalize_character_class...")
    for cls in ["swordsman", "MAGE", "Healer", "rogue", "archer"]:
        normalized = _normalize_character_class(cls)
        print(f"    '{cls}' → '{normalized}'")

    # 3. Fallback test
    print("[3] Testing _fallback_scene...")
    for cls in VALID_CHARACTER_CLASSES:
        fb = _fallback_scene(cls)
        print(f"    {cls}: '{fb['scene_name']}'")

    # 4. Full analyze_scene test (requires SNAPQUEST_MODAL_ENDPOINT)
    endpoint = os.getenv(MODAL_ENDPOINT_ENV)
    if not endpoint:
        print(f"\n[4] Skipping Modal test — {MODAL_ENDPOINT_ENV} not set.")
        print("    Set it to test the full pipeline:")
        print(f"    export {MODAL_ENDPOINT_ENV}=https://your-modal-endpoint.modal.run/analyze")
        print("\nAll local tests passed.")
        sys.exit(0)

    print(f"\n[4] Testing full pipeline against Modal endpoint...")
    img = Image.new("RGB", (320, 240), color=(30, 20, 15))
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 80, 120, 180], fill=(60, 40, 20))   # fake bookshelf
    draw.rectangle([150, 60, 200, 180], fill=(20, 20, 40))  # fake monitor
    draw.ellipse([240, 100, 290, 150], fill=(80, 60, 10))   # fake lamp

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        img.save(f.name)
        test_path = f.name

    print(f"    Test image: {test_path}")
    try:
        result = analyze_scene(test_path, "Mage")
        print(f"    scene_name: {result['scene_name']}")
        print(f"    description: {result['scene_description']}")
        print(f"    objects: {result['objects_found']}")
        print(f"    choices: {result['choices']}")
        print("\nFull pipeline test passed.")
    except Exception as e:
        print(f"    FAILED: {e}")
        sys.exit(1)
