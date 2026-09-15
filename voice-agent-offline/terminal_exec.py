"""
Terminal execution engine — generates and runs PowerShell commands from natural language.

Flow:
    1. User says something like "find all PDFs in my documents"
    2. LLM generates a PowerShell command as structured JSON
    3. If destructive → ask for voice confirmation
    4. Execute and return output (truncated for TTS)
"""

import subprocess
import json
import requests
from persona import build_system_prompt


def generate_command(user_request, model="local-model"):
    """Ask the LLM to generate a PowerShell command from natural language.
    
    Returns:
        dict with keys: command, description, destructive
        or None if generation failed
    """
    system = build_system_prompt("command")
    
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_request}
                ],
                "temperature": 0.2,  # Low temperature for precise command generation
                "max_tokens": 300,
            },
            timeout=30
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()
        
        # Strip markdown code fences if the model wraps its output
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()
        
        result = json.loads(raw)
        
        # Validate structure
        if "command" not in result or "description" not in result:
            print(f"[TERMINAL] Invalid command JSON: {raw[:200]}")
            return None
            
        # Default destructive to False if missing
        result.setdefault("destructive", False)
        
        return result
        
    except json.JSONDecodeError:
        print(f"[TERMINAL] LLM output was not valid JSON: {raw[:200]}")
        return None
    except requests.exceptions.ConnectionError:
        print("[TERMINAL] LM Studio not running.")
        return None
    except Exception as e:
        print(f"[TERMINAL] Command generation failed: {e}")
        return None


def execute_command(command, timeout=30):
    """Execute a PowerShell command and return the output.
    
    Args:
        command: The PowerShell command string to execute
        timeout: Max seconds to wait for the command to finish
        
    Returns:
        tuple: (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            if output:
                return True, output
            else:
                return True, "Command completed successfully with no output."
        else:
            # Command failed — return error
            return False, error if error else f"Command failed with exit code {result.returncode}."
            
    except subprocess.TimeoutExpired:
        return False, "Command timed out after 30 seconds."
    except Exception as e:
        return False, f"Failed to execute: {e}"


def summarize_output_for_speech(output, max_chars=500):
    """Truncate command output to a speakable length.
    
    Long outputs (like listing 200 files) need to be summarized 
    before being sent to TTS. If the output is a list, count items.
    """
    if not output:
        return "Done, no output."
    
    lines = output.strip().split("\n")
    lines = [l.strip() for l in lines if l.strip()]
    
    if len(lines) == 0:
        return "Done, no output."
    
    if len(lines) == 1:
        # Single line — just speak it (truncated)
        text = lines[0]
        if len(text) > max_chars:
            return text[:max_chars] + "... and more."
        return text
    
    # Multiple lines — likely a file listing or search result
    if len(lines) <= 10:
        # Small enough to read out
        joined = ". ".join(lines)
        if len(joined) > max_chars:
            return joined[:max_chars] + "... and more."
        return joined
    
    # Too many lines — summarize with count
    preview = ". ".join(lines[:5])
    remaining = len(lines) - 5
    return f"Found {len(lines)} results. Here are the first few: {preview}. And {remaining} more."


# ── Destructive command detection (fallback if LLM misses it) ────────────
DESTRUCTIVE_PATTERNS = [
    "remove-item", "del ", "delete", "rmdir", "rd ",
    "format", "clear-content", "set-content",
    "move-item", "rename-item",
    "stop-process", "kill",
    "uninstall",
    "reg delete", "remove-itemproperty",
]

def is_destructive(command):
    """Secondary safety check — catches destructive commands even if the LLM 
    marked destructive=false."""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in DESTRUCTIVE_PATTERNS)
