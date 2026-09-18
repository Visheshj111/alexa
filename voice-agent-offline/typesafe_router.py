"""
TypeSafe AI Jev - System One Cognitive Router
Provides typed, calibrated probabilistic decisions for intent classification
and action routing in ~70-150ms.
"""

import os
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
    "text": "General conversational questions, advice, reasoning, coding, or chit-chat"
}

def classify_intent_with_jev(text: str, confidence_threshold: float = 0.65) -> tuple[str | None, float | None]:
    """
    Use TypeSafe AI's Jev model to make a fast, typed System One decision on user intent.
    Returns (intent_name, confidence) if confident, or (None, None) if disabled, low confidence, or error.
    """
    client = get_typesafe_client()
    if not client:
        return None, None

    try:
        from typesafe_sdk import Choice, Noul

        response = client.system_one(
            state=text,
            questions={
                "intent": Choice(
                    instructions="Identify the primary intent or action requested by the user.",
                    criteria=JEV_INTENT_CRITERIA
                ),
                "is_urgent": Noul(
                    instructions="Does this request require immediate urgent or emergency intervention?"
                )
            }
        )

        if "intent" in response.choices:
            choice_ans = response.choices["intent"]
            intent = choice_ans.choice
            confidence = choice_ans.confidence
            
            if confidence >= confidence_threshold:
                print(f"[JEV System One] Decision: '{intent}' (confidence: {confidence:.2f})")
                return intent, confidence
            else:
                print(f"[JEV System One] Low confidence decision: '{intent}' ({confidence:.2f} < {confidence_threshold}). Deferring.")

    except Exception as e:
        print(f"[JEV] Warning during classification: {e}. Falling back to local rules.")

    return None, None
