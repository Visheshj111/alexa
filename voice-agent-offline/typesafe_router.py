"""
TypeSafe AI Jev - System One Cognitive Router
Provides typed, calibrated probabilistic decisions for intent classification
and action routing in ~70-150ms.
"""

import os
import threading
from pathlib import Path

def _load_env_file():
    """Load environment variables from .env in voice-agent-offline or project root."""
    env_paths = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for p in env_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env_file()

_client = None
_client_initialized = False
_decision_cache = {}

def get_typesafe_client():
    """Lazily initialize and return the TypeSafeClient if an API key is available."""
    global _client, _client_initialized
    if not _client_initialized:
        api_key = os.environ.get("TYPESAFE_API_KEY")
        if api_key:
            try:
                from typesafe_sdk import TypeSafeClient
                _client = TypeSafeClient(api_key=api_key)
                print("[JEV] TypeSafe AI Jev client initialized successfully.")
            except Exception as e:
                print(f"[JEV] Warning: Failed to initialize TypeSafeClient: {e}")
                _client = None
        else:
            _client = None
        _client_initialized = True
    return _client

def warmup_jev():
    """Asynchronously initialize TypeSafeClient and pre-warm TLS connection at boot."""
    def _do_warmup():
        client = get_typesafe_client()
        if client:
            try:
                from typesafe_sdk import Choice
                # Send a tiny warmup query to establish TLS/HTTP connection pool
                client.system_one(
                    state="ping",
                    questions={
                        "intent": Choice(
                            instructions="Warmup ping",
                            criteria={"ping": "ping check", "other": "other"}
                        )
                    }
                )
                print("[JEV] System One connection pre-warmed. Ready for instant routing.")
            except Exception as e:
                print(f"[JEV] Warmup ready.")
    threading.Thread(target=_do_warmup, daemon=True).start()

def is_jev_enabled() -> bool:
    """Check whether TypeSafe AI Jev is configured and available."""
    return get_typesafe_client() is not None

# Criteria definitions aligned with our full agent capabilities
JEV_INTENT_CRITERIA = {
    "app_open": "User wants to launch, start, or open a desktop application (e.g. 'open chrome', 'start vs code')",
    "app_close": "User wants to close, kill, or terminate a running application (e.g. 'close spotify', 'kill notepad')",
    "web_navigate": "User wants to open or navigate to a specific website or URL (e.g. 'go to github.com', 'open youtube')",
    "type": "User wants to type text or enter a prompt into the focused window (e.g. 'type hello world')",
    "click": "User wants to click, tap, or press a specific button or element on screen (e.g. 'click the submit button')",
    "media": "User wants to control audio/music playback, volume, mute, skip, or pause",
    "system": "User wants to adjust monitor brightness, lock the screen, or put the PC to sleep",
    "terminal": "User wants to execute a PowerShell command, shell script, or inspect disk space / processes",
    "file_search": "User wants to search for, find, or read the contents of a local file or folder",
    "vision": "User wants to inspect, look at, read, or analyze what is currently visible on their screen",
    "windows": "User wants to list or check what windows or applications are currently open",
    "reminder": "User wants to create a new reminder (e.g. 'remind me to drink water')",
    "list_reminders": "User wants to view, list, or check their saved reminders",
    "remember": "User explicitly tells the assistant to remember a preference or fact",
    "forget": "User asks the assistant to forget a previously stored memory",
    "blocklock": "User wants to block an application or website via BlockLock",
    "chat_mode": "User wants to switch to typing/chat mode instead of voice",
    "stop_listening": "User wants the assistant to stop listening or pause voice input",
    "shutdown": "User wants to exit, quit, power off, or terminate the assistant",
    "mode_switch": "User wants to switch version to 2.0 or 1.0, or give control to Jev or local AI",
    "improve_codebase": "User asks the assistant to improve the codebase, write code, add a feature, or use a tool like AntiGravity/Cursor",
    "text": "General conversational questions, advice, reasoning, coding, or chit-chat"
}

def classify_intent_with_jev(text: str, confidence_threshold: float = 0.65) -> dict | None:
    """
    Use TypeSafe AI's Jev model to make a fast, typed System One decision on user intent.
    Returns a dict with 'intent', 'target', 'payload', and 'tool_preference', or None.
    """
    norm_text = text.strip().lower()
    if norm_text in _decision_cache:
        return _decision_cache[norm_text]

    client = get_typesafe_client()
    if not client:
        return None

    try:
        from typesafe_sdk import Choice, Noul

        response = client.system_one(
            state=text,
            questions={
                "intent": Choice(
                    instructions="Identify the primary intent or action requested by the user.",
                    criteria=JEV_INTENT_CRITERIA
                ),
                "target": Noul(
                    instructions="If the user specified a target app, window, setting, or file, extract it here. (e.g. 'chrome', 'spotify', 'volume')"
                ),
                "payload": Noul(
                    instructions="If the user specified text to type, a search query, a URL, or specific instructions, extract it here."
                ),
                "tool_preference": Choice(
                    instructions="If the user specified an external tool for coding or delegation, extract it.",
                    criteria={
                        "antigravity_terminal": "User explicitly asked to use AntiGravity terminal or 'agy'",
                        "opencode": "User asked to use OpenCode or 'open code'",
                        "antigravity_gui": "User asked to use AntiGravity (without specifying terminal) or AntiGravity IDE",
                        "cursor": "User asked to use Cursor IDE",
                        "vscode": "User asked to use VS Code",
                        "none": "No tool was explicitly requested"
                    }
                )
            }
        )

        if "intent" in response.choices:
            choice_ans = response.choices["intent"]
            intent = choice_ans.choice
            confidence = choice_ans.confidence
            
            if confidence >= confidence_threshold:
                target = response.nouls.get("target")
                payload = response.nouls.get("payload")
                tool_pref = response.choices.get("tool_preference")
                tool_pref_val = tool_pref.choice if tool_pref and tool_pref.confidence > 0.5 else "none"
                
                result = {
                    "intent": intent,
                    "target": target,
                    "payload": payload,
                    "tool_preference": tool_pref_val,
                    "confidence": confidence
                }
                
                print(f"[JEV System One] Decision: '{intent}' (target: {target}, payload: {payload}, tool: {tool_pref_val})")
                _decision_cache[norm_text] = result
                return result
            else:
                print(f"[JEV System One] Low confidence decision: '{intent}' ({confidence:.2f} < {confidence_threshold}). Deferring.")

    except Exception as e:
        print(f"[JEV] Warning during classification: {e}. Falling back to local rules.")

    return None

