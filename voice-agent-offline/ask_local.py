import requests
import json
import re
from persona import build_system_prompt, build_context_prompt

def _build_system_with_memory():
    """Build the full system prompt with Jarvis identity + memory context."""
    return build_system_prompt("text")

def ask(question, model="local-model", system_override=None):
    from memory import get_recent_turns
    system = system_override if system_override else _build_system_with_memory()
    
    messages = [{"role": "system", "content": system}]
    for turn in get_recent_turns(n=5):
        messages.append({"role": "user", "content": turn['user']})
        messages.append({"role": "assistant", "content": turn['assistant']})
    messages.append({"role": "user", "content": question})

    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.75,
                "frequency_penalty": 1.2,
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

def ask_stream(question, model="local-model"):
    """Stream response from LM Studio and yield speakable sentence chunks as they arrive."""
    from memory import get_recent_turns
    system = _build_system_with_memory()
    
    messages = [{"role": "system", "content": system}]
    for turn in get_recent_turns(n=5):
        messages.append({"role": "user", "content": turn['user']})
        messages.append({"role": "assistant", "content": turn['assistant']})
    messages.append({"role": "user", "content": question})

    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": messages,
                "temperature": 0.75,
                "frequency_penalty": 1.2,
                "max_tokens": 300,
                "stream": True,
            },
            stream=True,
            timeout=30
        )
        response.raise_for_status()

        buffer = ""
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if line.startswith("data: ") and line.strip() != "data: [DONE]":
                try:
                    data = json.loads(line[6:])
                    delta = data["choices"][0].get("delta", {}).get("content", "")
                    if delta:
                        buffer += delta
                        parts = re.split(r'([.!?\n]+(?:\s+|$))', buffer)
                        if len(parts) > 1:
                            sentence = (parts[0] + parts[1]).strip()
                            if sentence:
                                yield sentence
                            buffer = ''.join(parts[2:])
                except json.JSONDecodeError:
                    pass
        if buffer.strip():
            yield buffer.strip()

    except requests.exceptions.ConnectionError:
        yield "LM Studio isn't running or the server isn't started."
    except requests.exceptions.Timeout:
        yield "LM Studio took too long to respond."
    except Exception as e:
        yield f"Error talking to LM Studio: {e}"

def ask_with_context(question, context_text, model="local-model"):
    """Ask a question about a specific piece of text (e.g. file contents)."""
    system = build_context_prompt(context_text)
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": question}
                ],
                "temperature": 0.3,
                "frequency_penalty": 1.2,
                "max_tokens": 400,
            },
            timeout=45
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
