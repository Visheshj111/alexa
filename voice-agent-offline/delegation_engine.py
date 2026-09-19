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
    import json
    from ask_local import ask
    from nerve_center import get_indexer
    
    indexer = get_indexer()
    if not indexer:
        speak_fn("Index not ready.")
        return
        
    # 1. Ask LLM to extract the specific target symbol (function/class/filename)
    extract_prompt = f"The user said: '{raw_prompt}'. Extract the core function, class, or file name they want to edit. Respond with ONLY the symbol name, nothing else. E.g., 'router', 'get_intent', etc."
    target_symbol = ask(extract_prompt).strip().strip("'\"").replace(" ", "_")
    
    print(f"[LOCAL EDIT] LLM extracted target symbol: {target_symbol}")
    
    results = indexer.find_target(target_symbol)
    if not results:
        speak_fn(f"I couldn't find anything matching {target_symbol} in the project.")
        return
        
    # Rank hits by how close they are to the exact name
    results.sort(key=lambda x: abs(len(x['file'].split('/')[-1]) - len(target_symbol)))
    best_match = results[0]
    file_path = best_match['file']
    abs_path = best_match['absolute_path']
    line_num = best_match['line']
    
    speak_fn(f"Found it in {os.path.basename(file_path)}. Preparing edit...")
    
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        edit_prompt = f"You are a local coding agent. User requested: '{raw_prompt}'.\nFile {file_path} contains the target around line {line_num}.\n\nOutput the exact replacement code block. Format as strict JSON:\n{{\"old\": \"exact old text to replace\", \"new\": \"new text\"}}"
        print(f"[LOCAL EDIT] Querying Qwen3 for diff...")
        response = ask(edit_prompt)
        
        # Clean JSON
        json_str = response.strip()
        if json_str.startswith("```json"): json_str = json_str[7:]
        elif json_str.startswith("```"): json_str = json_str[3:]
        if json_str.endswith("```"): json_str = json_str[:-3]
        
        diff = json.loads(json_str.strip())
        old_text = diff.get("old", "")
        new_text = diff.get("new", "")
        
        if old_text and old_text in content:
            new_content = content.replace(old_text, new_text, 1)
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            speak_fn("I have successfully applied the edit.")
            
            # Refresh the index!
            indexer.refresh()
        else:
            speak_fn("I generated an edit, but the old text didn't match the file exactly.")
            print(f"[LOCAL EDIT] Failed match.\nOld text generated: {old_text}")
            
    except Exception as e:
        print(f"[LOCAL EDIT] Error: {e}")
        speak_fn("I ran into a problem while trying to edit the file.")

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

