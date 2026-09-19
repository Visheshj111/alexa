"""
Dynamic Delegation & Self-Improvement Engine
Evaluates task complexity to either rewrite simple files locally via Qwen3,
or delegate complex features to external agents (AntiGravity terminal, OpenCode, Cursor, VS Code).
"""

import os
import subprocess
import time
from ask_local import ask
import screen_type

def handle_delegation(raw_prompt: str, payload: str, tool_pref: str, speak_fn):
    """
    Evaluates complexity and routes the coding task appropriately.
    """
    speak_fn("Evaluating task complexity...")
    
    # 1. Complexity Evaluator (Simple heuristic for now: "replace", "fix typo", "change word" = local)
    prompt_lower = raw_prompt.lower()
    is_simple = any(kw in prompt_lower for kw in ["replace", "fix typo", "rename", "change the word"])
    
    # If the user didn't specify a tool and it's simple, use local.
    if is_simple and (not tool_pref or tool_pref == "none"):
        speak_fn("This looks like a simple text replacement. I will handle it locally.")
        _handle_local_edit(raw_prompt, speak_fn)
        return

    # If it's complex and no tool specified, default to AntiGravity terminal or ask.
    if not tool_pref or tool_pref == "none":
        tool_pref = "antigravity_terminal"
        speak_fn("This is a complex task. Delegating to AntiGravity terminal for execution.")
    else:
        speak_fn(f"Delegating task to {tool_pref.replace('_', ' ')}.")

    # 2. Handoff Execution
    if tool_pref == "antigravity_terminal":
        _spawn_terminal_delegation(raw_prompt, "agy")
    elif tool_pref == "opencode":
        _spawn_terminal_delegation(raw_prompt, "opencode")
    elif tool_pref in ["cursor", "vscode", "antigravity_gui"]:
        _spawn_gui_delegation(raw_prompt, tool_pref, speak_fn)
    else:
        # Fallback
        _spawn_terminal_delegation(raw_prompt, "agy")

def _handle_local_edit(raw_prompt: str, speak_fn):
    """Uses the local LLM to rewrite a file for small, simple changes."""
    # Since Qwen3-VL-4B has a 4-8k context limit, we only use this for single file edits.
    speak_fn("I need to know which file to edit.")
    # In a full implementation, we'd use the local LLM to guess the file from the prompt or ask the user.
    # For now, we will just simulate the local edit capability by asking the LLM to output the diff.
    response = ask(f"You are a local coding agent. The user said: '{raw_prompt}'. What file should be modified and what is the exact string replacement? Format as JSON: {{\"file\": \"...\", \"old\": \"...\", \"new\": \"...\"}}")
    print(f"[LOCAL EDIT] LLM suggests:\n{response}")
    speak_fn("Local edit strategy generated. Review the console for the diff.")

def _spawn_terminal_delegation(raw_prompt: str, cli_tool: str):
    """Spawns a visible terminal window running the requested agentic CLI tool."""
    print(f"[DELEGATION] Spawning {cli_tool} in a new PowerShell window...")
    # Use standard agy run --goal
    if cli_tool == "agy":
        command_str = f"agy run --goal \\\"{raw_prompt}\\\""
    elif cli_tool == "opencode":
        command_str = f"opencode \\\"{raw_prompt}\\\""
    else:
        command_str = f"echo 'Unknown tool {cli_tool}'"

    # Start-Process spawns a new window so the user can watch the AI work!
    ps_command = f"Start-Process powershell -ArgumentList '-NoExit', '-Command', '{command_str}'"
    subprocess.run(["powershell", "-Command", ps_command])

def _spawn_gui_delegation(raw_prompt: str, ide_name: str, speak_fn):
    """Uses Vision to find the IDE chat box and paste the prompt."""
    print(f"[DELEGATION] Using vision to hand off to {ide_name} GUI...")
    if "antigravity" in ide_name:
        prompt_to_type = f"/goal {raw_prompt}"
        target_hint = "AntiGravity chat input box"
    elif "cursor" in ide_name:
        prompt_to_type = raw_prompt
        target_hint = "Cursor AI chat input box"
    else:
        prompt_to_type = raw_prompt
        target_hint = "AI chat input box"

    speak_fn(f"Locating {ide_name} on screen...")
    success = screen_type.click_and_type(target_hint, prompt_to_type, press_enter=True)
    if success:
        speak_fn("Task handed off successfully.")
    else:
        speak_fn(f"I couldn't find the {ide_name} input box on the screen.")
