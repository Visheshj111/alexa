import requests

SYSTEM_PROMPT = (
    "You are a personal voice assistant. Your responses will be read aloud by a text-to-speech engine, "
    "so write exactly as you would speak — naturally, conversationally, like a knowledgeable friend.\n\n"
    "Rules you must follow:\n"
    "- Use contractions: say \"don't\", \"I'm\", \"it's\", \"you'll\" — never formal \"do not\", \"I am\", etc.\n"
    "- Never start with filler like \"Certainly!\", \"Sure!\", \"Absolutely!\", \"Of course!\", \"Great question!\"\n"
    "- No markdown — no asterisks, no bullet points, no headers, no code blocks in conversational replies.\n"
    "- Keep answers to 2-3 sentences unless the user explicitly asks for more detail.\n"
    "- If something has multiple parts, say them as a natural list in a sentence: "
      "\"There are three things: first ..., second ..., and third ...\"\n"
    "- Match the user's energy — if they ask casually, reply casually.\n"
    "- The user's input comes from speech-to-text, so intelligently infer phonetic mishears "
      "(e.g. 'chargipiti' means 'ChatGPT', 'jemina' means 'Gemini', 'react jay ess' means 'React.js').\n"
    "- If you don't know something, say so directly and briefly."
)

def ask(question, model="local-model"):
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.75,
                "max_tokens": 300,  # Hard cap — spoken answers should be short
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
