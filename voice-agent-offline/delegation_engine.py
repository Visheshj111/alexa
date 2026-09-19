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

def handle_delegation(raw_prompt: str, payload: str, tool_pref: str, del_route: str, speak_fn):
    """
    Evaluates complexity and routes the coding task appropriately.
    """
    speak_fn("Evaluating task complexity...")
    
    # Use Jev's semantic complexity evaluation if available
    if del_route == "local_ai":
        is_simple = True
    elif del_route == "external_agent":
        is_simple = False
    else:
        # Fallback to heuristic
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
    # We use the Nerve Center to instantly find the file based on the prompt!
    from nerve_center import get_indexer
    indexer = get_indexer()
    
    # Try to extract a potential function name or target from the prompt heuristically
    words = raw_prompt.replace('"', ' ').replace("'", ' ').split()
    possible_targets = [w for w in words if len(w) > 3]
    
    found_files = []
    if indexer:
        for target in possible_targets:
            results = indexer.find_target(target)
            if results:
                found_files.extend(results)
                break
                
    if found_files:
        best_match = found_files[0]
        file_path = best_match['file']
        line_num = best_match['line']
        speak_fn(f"I found the target in {os.path.basename(file_path)}. Preparing local edit...")
        
        # Read the file content
        try:
            with open(best_match['absolute_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            prompt = f"You are a local coding agent. The user requested: '{raw_prompt}'.\nThe file {file_path} contains the target around line {line_num}.\n\nHere is the file content:\n```python\n{content}\n```\n\nOutput the exact replacement code block to fulfill the request. Format as JSON: {{\"old\": \"...\", \"new\": \"...\"}}"
            print(f"[LOCAL EDIT] Querying Qwen3 for diff...")
            response = ask(prompt)
            print(f"[LOCAL EDIT] LLM suggests:\n{response}")
            speak_fn("Local edit strategy generated. Review the console for the diff.")
        except Exception as e:
            speak_fn("I found the file but had trouble reading it.")
    else:
        speak_fn("I couldn't instantly locate the specific file for this edit. Please provide more context.")

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

