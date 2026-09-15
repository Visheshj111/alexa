"""
Web server for mobile/browser access to Alexa.

Runs on 0.0.0.0:8080 so any device on the same WiFi can reach it.
Your phone connects to http://<laptop-ip>:8080 and gets a chat interface.
All processing stays on the laptop — the phone is just a thin client.
"""

import os
import sys
import re
import socket
import json
import webbrowser

from flask import Flask, request, jsonify, render_template

# Add the voice-agent-offline directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ask_local import ask
from ask_vision import ask_with_image
from screenshot import capture_screen_base64
from screen_click import scale_coordinates, execute_click, get_actual_screen_size
import screen_type
from memory import save_turn, add_explicit_memory, forget_memory, start_new_session, build_memory_context
from terminal_exec import generate_command, execute_command, summarize_output_for_speech, is_destructive

app = Flask(__name__)

# Start a session for the web client
start_new_session()

def clean_command_text(text):
    if not text:
        return ""
    prefix_pattern = r'^(?:can you\s+)?(?:look at|see|check|view)\s+(?:my|the)?\s*screen\s+(?:and\s+)?'
    cleaned = re.sub(prefix_pattern, '', text, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'^(?:on|from)\s+(?:my|the)?\s*screen\s+', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else text

def get_intent(text):
    cleaned = clean_command_text(text).lower()
    
    if any(kw in cleaned for kw in ["remember that", "remember this", "don't forget"]):
        return "remember"
    if any(kw in cleaned for kw in ["forget that", "forget about"]):
        return "forget"

    if (cleaned.startswith("go to ") or cleaned.startswith("navigate to ") or cleaned.startswith("open site ") or cleaned.startswith("open website ")) and any(ext in cleaned for ext in [".com", ".org", ".net", ".io", ".gov", "facebook", "youtube", "google", "github", "twitter", "x.com", "reddit"]):
        return "web_navigate"
    if any(domain in cleaned for domain in ["facebook.com", "youtube.com", "google.com", "github.com", "twitter.com", "x.com", "reddit.com"]):
        return "web_navigate"

    if any(kw in cleaned for kw in [
        "type ", "write a prompt", "write prompt", "type prompt", "type a prompt",
        "enter text", "write this", "put text", "input text", "enter prompt",
        "write a", "write the prompt"
    ]) or ("type" in cleaned and "typing mode" not in cleaned):
        return "type"

    if any(kw in cleaned for kw in ["click", "press the", "tap the", "select the"]):
        return "click"

    if any(kw in cleaned for kw in ["screen", "looking at", "read this", "see this", "on my display", "what am i looking at"]):
        return "vision"

    if any(kw in cleaned for kw in [
        "find all", "list all", "get all", "get me all", "delete",
        "deep search", "scan", "terminal", "powershell", "execute",
        "disk space", "storage space", "running processes",
        "create a folder", "open the folder", "open folder",
        "rename", "move this", "move the",
    ]):
        return "terminal"
    if any(kw in cleaned for kw in ["open ", "launch ", "start "]):
        return "app_open"
    if any(kw in cleaned for kw in ["close ", "kill ", "terminate "]):
        return "app_close"
    if any(kw in cleaned for kw in ["brightness", "lock screen", "lock my", "sleep"]):
        return "system"
    if any(kw in cleaned for kw in ["play", "pause", "skip", "next song", "volume", "mute"]):
        return "media"
    
    return "text"


@app.route("/")
def index():
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"response": "I didn't catch that.", "type": "text"})
    
    # Clean filler
    filler_pattern = r'\b(hey|can you|could you|please|alexa|would you|just)\b'
    cleaned = re.sub(filler_pattern, '', message, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    intent = get_intent(cleaned)
    
    try:
        if intent == "remember":
            fact = cleaned
            for prefix in ["remember that", "remember this", "don't forget that", "don't forget"]:
                if prefix in fact.lower():
                    fact = fact[fact.lower().index(prefix) + len(prefix):].strip()
                    break
            if fact:
                result = add_explicit_memory(fact)
                return jsonify({"response": result, "type": "action"})
            return jsonify({"response": "What should I remember?", "type": "text"})

        elif intent == "forget":
            fact = cleaned
            for prefix in ["forget that", "forget about"]:
                if prefix in fact.lower():
                    fact = fact[fact.lower().index(prefix) + len(prefix):].strip()
                    break
            if fact:
                result = forget_memory(fact)
                return jsonify({"response": result, "type": "action"})
            return jsonify({"response": "What should I forget?", "type": "text"})

        elif intent == "click":
            cleaned = clean_command_text(message)
            image_b64 = capture_screen_base64()
            click_prompt = f"Find the UI element to click for: '{cleaned}'."
            response = ask_with_image(click_prompt, image_b64, mode="click")
            try:
                x_str, y_str, desc = response.split(",", 2)
                x, y = int(x_str.strip()), int(y_str.strip())
                actual_width, actual_height = get_actual_screen_size()
                real_x, real_y = scale_coordinates(x, y, actual_width, actual_height)
                execute_click(real_x, real_y)
                return jsonify({"response": f"Clicked {desc.strip()} at ({real_x}, {real_y}).", "type": "action"})
            except Exception as e:
                return jsonify({"response": f"Could not locate element to click: {e}", "type": "error"})

        elif intent == "type":
            cleaned = clean_command_text(message)
            needs_refinement = any(kw in cleaned.lower() for kw in ["prompt", "enhance", "write a prompt", "create a prompt", "refine"])
            press_enter = any(kw in cleaned.lower() for kw in ["enter it", "submit", "press enter", "and enter", "and send"])
            text_to_type = cleaned
            for prefix in ["type ", "write a prompt to ", "write prompt to ", "write a prompt ", "write ", "enter text ", "put text "]:
                if cleaned.lower().startswith(prefix):
                    text_to_type = cleaned[len(prefix):].strip()
                    break
            if needs_refinement:
                text_to_type = screen_type.refine_prompt_for_ai(text_to_type)
            screen_type.type_text(text_to_type, press_enter=press_enter)
            return jsonify({"response": f"Typed text into active window: {text_to_type[:100]}...", "type": "action"})

        elif intent == "web_navigate":
            cleaned = clean_command_text(message)
            url = cleaned
            for prefix in ["go to website ", "go to site ", "go to ", "navigate to ", "open site ", "open website ", "open "]:
                if cleaned.lower().startswith(prefix):
                    url = cleaned[len(prefix):].strip()
                    break
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            webbrowser.open(url)
            display_domain = url.replace("https://", "").replace("http://", "").split("/")[0]
            return jsonify({"response": f"Opening {display_domain} in browser.", "type": "action"})

        elif intent == "vision":
            b64 = capture_screen_base64()
            answer = ask_with_image(message, b64, mode="vision")
            save_turn(message, answer)
            return jsonify({"response": answer, "type": "vision"})

        elif intent == "terminal":
            cmd_result = generate_command(message)
            if cmd_result is None:
                return jsonify({"response": "I couldn't figure out the right command. Try rephrasing.", "type": "error"})
            
            command = cmd_result["command"]
            description = cmd_result["description"]
            destructive = cmd_result.get("destructive", False) or is_destructive(command)
            
            if destructive:
                return jsonify({
                    "response": f"⚠️ This will {description}.\nCommand: `{command}`\n\nSend 'confirm' to execute or anything else to cancel.",
                    "type": "confirm",
                    "pending_command": command
                })
            
            success, output = execute_command(command)
            save_turn(message, f"[Executed: {command}] {output[:200]}")
            return jsonify({
                "response": f"{'✓' if success else '✗'} {output}",
                "type": "terminal",
                "command": command
            })

        elif intent == "app_open":
            from app_control import open_app
            result = open_app(cleaned)
            return jsonify({"response": result, "type": "action"})

        elif intent == "app_close":
            from app_control import close_app
            result = close_app(cleaned)
            return jsonify({"response": result, "type": "action"})

        elif intent == "media":
            from media_control import media_play_pause, media_next, media_previous, media_volume_up, media_volume_down, media_mute, media_set_volume
            match = re.search(r'volume.*?(\d+)', message)
            if match:
                result = media_set_volume(int(match.group(1)))
            elif any(kw in message for kw in ["next", "skip"]):
                result = media_next()
            elif any(kw in message for kw in ["previous", "back"]):
                result = media_previous()
            elif any(kw in message for kw in ["volume up", "louder"]):
                result = media_volume_up()
            elif any(kw in message for kw in ["volume down", "quieter"]):
                result = media_volume_down()
            elif any(kw in message for kw in ["mute", "unmute"]):
                result = media_mute()
            else:
                result = media_play_pause()
            return jsonify({"response": result, "type": "action"})

        elif intent == "system":
            from system_control import change_brightness, lock_screen, sleep_system, set_brightness
            match = re.search(r'brightness.*?(\d+)', message)
            if match:
                result = set_brightness(int(match.group(1)))
            elif any(kw in message for kw in ["lock"]):
                result = lock_screen()
            elif any(kw in message for kw in ["sleep"]):
                result = sleep_system()
            else:
                result = "I can change brightness, lock the screen, or put the PC to sleep."
            return jsonify({"response": result, "type": "action"})

        else:
            answer = ask(message)
            save_turn(message, answer)
            return jsonify({"response": answer, "type": "text"})
    
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}", "type": "error"})


@app.route("/confirm", methods=["POST"])
def confirm_command():
    """Execute a previously confirmed destructive command."""
    data = request.get_json()
    command = data.get("command", "")
    
    if not command:
        return jsonify({"response": "No command to execute.", "type": "error"})
    
    success, output = execute_command(command)
    return jsonify({
        "response": f"{'✓' if success else '✗'} {output}",
        "type": "terminal",
        "command": command
    })


def get_local_ip():
    """Get the machine's local WiFi IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    local_ip = get_local_ip()
    port = 8080
    
    print("=" * 55)
    print("  ALEXA — Web Chat Server")
    print("=" * 55)
    print(f"  Local:   http://localhost:{port}")
    print(f"  Network: http://{local_ip}:{port}")
    print(f"\n  Open the Network URL on your phone to chat!")
    print("=" * 55)
    
    app.run(host="0.0.0.0", port=port, debug=False)
