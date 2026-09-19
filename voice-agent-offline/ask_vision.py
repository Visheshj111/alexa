import requests
import json
import base64
import os
from persona import build_system_prompt


def ask_with_image(question, base64_image, model="local-model", mode="vision", retries=1):
    """Send a screenshot to the vision model with the Jarvis persona.
    
    Args:
        question: The user's question/request about the screen
        base64_image: Base64-encoded JPEG screenshot
        model: LM Studio model identifier
        mode: "vision" for general screen analysis, "click" for coordinate extraction
        retries: Number of retries on model reload
    """
    data_uri = f"data:image/jpeg;base64,{base64_image}"
    system = build_system_prompt(mode)
    
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                "http://localhost:1234/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": system
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": question},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": data_uri
                                    }
                                }
                            ]
                        }
                    ],
                    "temperature": 0.3 if mode in ["click", "interactive_type"] else 0.7,
                    "max_tokens": 1024
                },
                timeout=90
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if "Model reloaded" in e.response.text and attempt < retries:
                print("LM Studio reloaded the model. Retrying...")
                continue
            return f"HTTP Error talking to LM Studio vision endpoint: {e}\nResponse body: {e.response.text}"
        except requests.exceptions.ConnectionError:
            return "LM Studio isn't running or the server isn't started. Check it."
        except requests.exceptions.Timeout:
            return "LM Studio took too long to respond."
        except Exception as e:
            return f"Error talking to LM Studio vision endpoint: {e}"

if __name__ == "__main__":
    print("Testing ask_with_image...")
    
    # Create a simple synthetic image using PIL for the standalone test
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    img = Image.new('RGB', (800, 600), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Hello from synthetic test image!", fill=(255,255,0))
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    print(f"Generated test image base64, length: {len(b64)}")
    print("Sending to LM Studio...")
    
    response = ask_with_image("What text is written on this image, and what is its background color?", b64)
    print(f"\nLM Studio Response:\n{response}")
