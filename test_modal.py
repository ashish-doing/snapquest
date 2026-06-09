import modal
import base64

app = modal.App("snapquest-test")

image = modal.Image.debian_slim().pip_install(
    "torch", "Pillow", "requests"
)

@app.function(gpu="T4", image=image, timeout=120)
def test_vision(image_b64: str) -> str:
    import requests, torch
    from PIL import Image
    import io, base64, json

    # Test with HF inference API first (faster than loading full model)
    headers = {"Content-Type": "application/json"}
    payload = {
        "inputs": "Describe all objects you see in this room in a JSON list.",
        "parameters": {"max_new_tokens": 200}
    }
    return f"Modal GPU working. torch.cuda.is_available()={torch.cuda.is_available()}"

@app.local_entrypoint()
def main():
    result = test_vision.remote("")
    print("RESULT:", result)