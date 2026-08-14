import requests
import json
import base64
import os

def ask_with_image(question, base64_image, model="qwen3-vl-4b-instruct"):
    try:
        data_uri = f"data:image/jpeg;base64,{base64_image}"
        
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise, helpful study assistant. Keep answers brief as they will be spoken aloud."
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
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=90
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "LM Studio isn't running or the server isn't started. Check it."
    except requests.exceptions.Timeout:
        return "LM Studio took too long to respond."
    except requests.exceptions.HTTPError as e:
        return f"HTTP Error talking to LM Studio vision endpoint: {e}\nResponse body: {e.response.text}"
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
