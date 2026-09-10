"""Safe, explicit voice-command adapter for the local BlockLock CLI."""
import os
import re
import shutil
import subprocess
from pathlib import Path


CLI = Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "BlockLock" / "blocklockctl.py"
PYTHON_LAUNCHER = shutil.which("py") or "py"


def _run(*args):
    if not CLI.exists():
        return "BlockLock is not installed yet. Run its installer as Administrator first."
    try:
        completed = subprocess.run(
            [PYTHON_LAUNCHER, "-3", str(CLI), *args],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except OSError as error:
        return f"I couldn't start BlockLock: {error}"
    output = (completed.stdout or completed.stderr).strip()
    return output or "BlockLock did not return a response."


def handle_voice_command(text):
    """Return (spoken_response, terminal_response) for an explicit command."""
    command = text.lower().strip()

    if any(word in command for word in ("status", "state", "what is blocked")):
        result = _run("status")
        return result.replace("\n", ". "), result

    if any(phrase in command for phrase in ("list apps", "list applications", "show apps", "show applications")):
        result = _run("apps")
        return "I printed the running applications in the terminal.", result

    if any(word in command for word in ("unlock", "disable")) or "turn off blocklock" in command:
        result = _run("unlock")
        return result, result

    if any(phrase in command for phrase in ("lock blocklock", "blocklock lock", "enable blocklock", "turn on blocklock", "start blocking")):
        result = _run("lock")
        return result, result

    site = re.search(r"(?:block|add)\s+(?:the\s+)?(?:site|website|domain)\s+(.+)", command)
    if site:
        value = re.sub(r"\b(please|for me)\b", "", site.group(1)).strip().replace(" dot ", ".").strip(".")
        value = value.replace(" ", "")
        if not re.fullmatch(r"[a-z0-9.-]+", value):
            return "I need a valid site name, such as reddit dot com.", "Invalid site name."
        result = _run("add-site", value)
        return result, result

    app = re.search(r"(?:block|add)\s+(?:the\s+)?(?:app|application|process)\s+(.+)", command)
    if app:
        value = re.sub(r"\b(please|for me)\b", "", app.group(1)).strip()
        if value:
            result = _run("add-process", value)
            return result, result

    return (
        "Try: BlockLock status, lock BlockLock, unlock BlockLock, block application Steam, or block site example dot com.",
        "Unrecognized BlockLock voice command.",
    )
