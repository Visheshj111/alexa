import requests
from memory import build_memory_context

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
    "- If you don't know something, say so directly and briefly.\n"
    "- You have a memory of past conversations. Use it to personalize your responses. "
      "If the user asks about themselves, your opinions of them, or references past interactions, "
      "use your memory to give a real, personal answer — never say 'I don't have memory' or "
      "'I'm just an AI'. You DO remember. Act like it."
)

def _build_system_with_memory():
    """Combine the base system prompt with any available memory context."""
    memory = build_memory_context()
    if memory:
        return SYSTEM_PROMPT + "\n\n" + memory
    return SYSTEM_PROMPT

def ask(question, model="local-model"):
    system = _build_system_with_memory()
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
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

def ask_with_context(question, context_text, model="local-model"):
    """Ask a question about a specific piece of text (e.g. file contents)."""
    memory = build_memory_context()
    system = (
        "You are a personal voice assistant. Your response will be read aloud, "
        "so reply naturally and conversationally — no markdown, no bullet points, no headers.\n\n"
        "The user has asked you a question about the contents of a file on their PC. "
        "The file's contents are provided below between the markers. "
        "Answer only from the file contents. If the answer isn't in the file, say so directly.\n\n"
        f"--- FILE CONTENTS ---\n{context_text}\n--- END OF FILE ---"
    )
    if memory:
        system = system + "\n\n" + memory
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.3,  # Lower temp = more factual, less creative
                "max_tokens": 400,
            },
            timeout=45  # File queries might be slightly slower
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "LM Studio isn't running."
    except requests.exceptions.Timeout:
        return "LM Studio took too long. The file might be too large."
    except Exception as e:
        return f"Error: {e}"

def consolidate_memory(model="local-model"):
    """Ask the LLM to PROPOSE memory changes, then validate and merge them.
    The LLM never directly writes to memory.json."""
    from memory import get_consolidation_prompt, parse_consolidation_output, apply_proposed_changes
    prompt = get_consolidation_prompt()
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 800,
            },
            timeout=60
        )
        response.raise_for_status()
        raw_output = response.json()["choices"][0]["message"]["content"]

        # Step 1: Parse and validate the LLM's proposal
        proposal = parse_consolidation_output(raw_output)
        if proposal is None:
            print("[MEMORY] Consolidation proposal rejected.")
            return False

        # Step 2: Apply validated changes through the merge engine
        changes = apply_proposed_changes(proposal)
        if changes:
            print(f"[MEMORY] Applied {len(changes)} changes:")
            for c in changes:
                print(f"  → {c}")
        else:
            print("[MEMORY] No changes needed.")
        return True

    except Exception as e:
        print(f"[MEMORY] Consolidation failed: {e}")
        return False

