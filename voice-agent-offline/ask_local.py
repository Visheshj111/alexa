import requests

def ask(question, model="qwen3-vl-4b-instruct"):
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a concise, helpful study assistant. Keep answers brief as they will be spoken aloud. The user's input comes from a speech-to-text engine, so please intelligently infer the meaning of obvious phonetic misspellings (e.g., 'chargipiti' means 'ChatGPT', 'jemina' means 'Gemini')."},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.7,
                "max_tokens": 1024
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "LM Studio isn't running or the server isn't started. Check it."
    except requests.exceptions.Timeout:
        return "LM Studio took too long to respond."
    except Exception as e:
        return f"Error talking to LM Studio: {e}"
