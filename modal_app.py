"""SnapQuest MiniCPM-V 4.6 Modal deployment — Modal 1.4.3, Transformers 5.x

Deploy:  modal deploy modal_app.py
"""
from __future__ import annotations
import base64
import io
from typing import Any
import modal

MODEL_ID = "openbmb/MiniCPM-V-4.6"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "transformers>=5.7.0",
        "torch",
        "torchvision",
        "av",
        "Pillow",
        "accelerate",
        "huggingface_hub",
        "fastapi[standard]",
    )
    .run_commands(
        "python -c \""
        "from huggingface_hub import snapshot_download; "
        f"snapshot_download(repo_id='{MODEL_ID}', local_dir='/model', "
        "ignore_patterns=['*.gguf', 'gguf*'])"
        "\""
    )
)

app = modal.App("snapquest-minicpm-v-46")


def _extract_input(messages: list[dict[str, Any]]) -> tuple[str, str, bytes]:
    system_prompt = ""
    user_text_parts: list[str] = []
    image_data = b""

    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role == "system":
            if isinstance(content, str):
                system_prompt = content
            continue
        if role != "user":
            continue
        if isinstance(content, str):
            user_text_parts.append(content)
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                user_text_parts.append(str(block.get("text", "")))
            elif block.get("type") == "image":
                source = block.get("source", {})
                if source.get("type") == "base64":
                    image_data = base64.b64decode(source.get("data", ""))

    if not image_data:
        raise ValueError("No base64 image found in messages.")
    return system_prompt, "\n".join(p for p in user_text_parts if p), image_data


@app.cls(
    image=image,
    gpu="A10G",
    timeout=300,
    scaledown_window=300,
)
class MiniCPMVService:

    @modal.enter()
    def load_model(self) -> None:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.processor = AutoProcessor.from_pretrained(
            "/model", trust_remote_code=True
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            "/model",
            trust_remote_code=True,
            torch_dtype="auto",
            device_map="auto",
        )
        self.model.eval()

    @modal.fastapi_endpoint(method="POST")
    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        from PIL import Image
        import torch

        messages = payload.get("messages")
        if not isinstance(messages, list):
            return {"error": "messages must be a list"}

        temperature = float(payload.get("temperature", 0.4))
        max_tokens = int(payload.get("max_tokens", 500))

        try:
            system_prompt, user_text, image_bytes = _extract_input(messages)
        except ValueError as e:
            return {"error": str(e)}

        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        prompt = f"{system_prompt}\n\n{user_text}" if system_prompt else user_text

        # Correct transformers 5.x API for MiniCPM-V 4.6
        msgs = [{"role": "user", "content": [{"type": "image", "image": pil_image}, {"type": "text", "text": prompt}]}]

        inputs = self.processor.apply_chat_template(
            msgs,
            add_generation_prompt=True,
            tokenize=True,
            return_tensors="pt",
            return_dict=True,
        ).to("cuda")

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=temperature if temperature > 0 else 1.0,
            )

        input_len = inputs["input_ids"].shape[1]
        answer = self.processor.decode(
            output_ids[0][input_len:], skip_special_tokens=True
        )

        return {"choices": [{"message": {"content": answer}}]}


if __name__ == "__main__":
    buffer = io.BytesIO()
    from PIL import Image
    Image.new("RGB", (64, 64), color=(32, 64, 96)).save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    payload = {
        "messages": [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": encoded}},
                {"type": "text", "text": "Describe this image."},
            ]},
        ],
    }
    system, text, img_bytes = _extract_input(payload["messages"])
    print(f"OK — system:{len(system)}c text:{text} image:{len(img_bytes)}b")
    print("Deploy with: modal deploy modal_app.py")