from wake_word import listen_for_wake_word
from speaker_verify import verify_speaker
from transcribe import transcribe_audio
from ask_local import ask, ask_with_context, consolidate_memory
from speak import speak, speak_cached, precache_phrases
from memory import save_turn, add_explicit_memory, forget_memory, start_new_session
from screenshot import capture_screen_base64
from ask_vision import ask_with_image
from window_enum import get_open_windows
import sounddevice as sd
import soundfile as sf
import re
import numpy as np
import time
import random
from concurrent.futures import ThreadPoolExecutor

def get_intent(text):
    text = text.lower()
    
    if text.startswith("remind me"):
        return "reminder"
        
    if any(kw in text for kw in ["what are my reminders", "list my reminders", "read my reminders", "do i have any reminders"]):
        return "list_reminders"

    if any(kw in text for kw in ["remember that", "remember this", "don't forget", "change what you remember", "change my preference"]):
        return "remember"

    if any(kw in text for kw in ["forget that", "forget about", "stop remembering"]):
        return "forget"

    if any(kw in text for kw in ["stop listening", "don't listen", "do not listen", "avoid listening"]):
        return "stop_listening"

    if any(kw in text for kw in ["shut down", "go to sleep forever", "turn off", "exit", "quit", "power off"]):
        return "shutdown"
        
    # check BEFORE the generic "open" check below, since phrases like
    # "what apps are open" contain "open" but mean enumeration, not launching
    if any(kw in text for kw in ["open apps", "open windows", "what's open", "running right now", "list windows", "what apps"]):
        return "windows"

    if any(kw in text for kw in ["open ", "launch ", "start "]):
        return "app_open"

    if any(kw in text for kw in ["close ", "kill ", "quit ", "shut ", "terminate "]) and not any(kw in text for kw in ["shut down", "quit", "exit"]):
        # Wait, shutdown is handled earlier, but let's be careful not to conflict
        return "app_close"

    if any(kw in text for kw in ["find a file", "search for a file", "find the file", "read the file", "what's in the file", "file called", "file named", "search in"]):
        return "file_search"

    if any(kw in text for kw in ["click", "press the", "tap the", "select the"]):
        return "click"

    if any(kw in text for kw in ["brightness", "lock screen", "lock the screen", "lock my pc", "lock my computer", "sleep", "go to sleep", "put the pc to sleep", "put the computer to sleep"]):
        return "system"

    if any(kw in text for kw in ["play", "pause", "skip", "next song", "previous song", "volume", "mute", "unmute", "louder", "quieter", "turn it up", "turn it down", "stop the music", "start the music"]):
        return "media"

    if any(kw in text for kw in ["screen", "looking at", "read this", "see this", "on my display", "what am i looking at"]):
        return "vision"

    return "text"


def split_commands(text):
    import re
    parts = re.split(r'\s*\b(and then|and|then)\b\s*', text, flags=re.IGNORECASE)
    if len(parts) == 1:
        return [text]
    commands = []
    current_command = parts[0]
    for i in range(1, len(parts), 2):
        delimiter = parts[i]
        next_chunk = parts[i+1]
        cleaned_next = re.sub(r'\b(hey|can you|could you|please|alexa|would you|just|go ahead and|i want you to|i need you to)\b', '', next_chunk, flags=re.IGNORECASE).strip()
        if get_intent(cleaned_next) != "text" and cleaned_next != "":
            commands.append(current_command.strip())
            current_command = next_chunk
        else:
            current_command = current_command + " " + delimiter + " " + next_chunk
    if current_command.strip():
        commands.append(current_command.strip())
    return [c for c in commands if c]

def record_clip(filename="clip.wav", silence_limit=1.5, max_seconds=15, seconds=None, wait_timeout=None):
    samplerate = 16000
    chunk_duration = 0.1
    chunk_samples = int(samplerate * chunk_duration)
    
    print("\n🎙️ Listening... (Speak now!)")
    
    recorded_frames = []
    silent_chunks = 0
    has_spoken = False
    
    with sd.InputStream(samplerate=samplerate, channels=1, dtype='float32', blocksize=chunk_samples) as stream:
        # Dynamically calculate background noise threshold for 0.5s
        bg_noise = []
        for _ in range(5):
            chunk, _ = stream.read(chunk_samples)
            bg_noise.append(np.max(np.abs(chunk)))
        threshold = max(0.005, np.mean(bg_noise) * 2.5)
        
        start_time = time.time()
        
        while True:
            chunk, overflowed = stream.read(chunk_samples)
            recorded_frames.append(chunk)
            
            volume = np.max(np.abs(chunk))
            
            # If fixed duration requested, bypass silence logic
            if seconds is not None:
                if (time.time() - start_time) >= seconds:
                    break
                continue

            if volume > threshold:
                has_spoken = True
                silent_chunks = 0
            elif has_spoken:
                silent_chunks += 1
                
            # Timeout if they never start speaking
            if wait_timeout is not None and not has_spoken:
                if (time.time() - start_time) > wait_timeout:
                    return None
                
            # Stop if user finishes speaking
            if has_spoken and silent_chunks > (silence_limit / chunk_duration):
                break
                
            # Failsafe stop
            if (time.time() - start_time) > max_seconds:
                break
                
    audio_data = np.concatenate(recorded_frames, axis=0)
    sf.write(filename, audio_data, samplerate, subtype='PCM_16')
    return filename

def handle_click_intent(question, record_clip_fn, transcribe_fn, speak_fn):
    from ask_vision import ask_with_image
    from screenshot import capture_screen_base64
    from screen_click import scale_coordinates, execute_click, get_actual_screen_size

    RESIZED_MAX_EDGE = 1280  # must match whatever screenshot.py actually resizes to

    image_b64 = capture_screen_base64()
    vision_prompt = (
        f"Find the UI element to click for: '{question}'. "
        f"Respond ONLY in this format: X,Y,DESCRIPTION "
        f"where X and Y are normalized coordinates from 0 to 1000 (0,0 is top-left). "
        f"HINT: Standard Windows window controls (close, maximize, minimize) are at the VERY top edge (Y is usually between 0 and 20). "
        f"DESCRIPTION must be a short label of what you're clicking."
    )
    response = ask_with_image(vision_prompt, image_b64)

    try:
        x_str, y_str, desc = response.split(",", 2)
        x, y = int(x_str.strip()), int(y_str.strip())
    except Exception:
        speak_fn("I couldn't figure out exactly what to click. Try being more specific.")
        return

    actual_width, actual_height = get_actual_screen_size()
    real_x, real_y = scale_coordinates(x, y, RESIZED_MAX_EDGE, actual_width, actual_height)

    speak_fn(f"About to click {desc.strip()}. Say yes to confirm, or no to cancel.")
    confirm_clip = record_clip_fn(seconds=3)
    confirm_text = transcribe_fn(confirm_clip).lower()

    if any(word in confirm_text for word in ["yes", "yeah", "confirm", "do it", "go ahead"]):
        execute_click(real_x, real_y)
        speak_fn("Done.")
    else:
        speak_fn("Cancelled.")

def main_loop():
    WAKE_PHRASES = [
        "Yes boss.",
        "I'm right here, what do you want.",
        "Oh, it's you. What now.",
        "At your service, unfortunately.",
        "Here we go again. What is it.",
        "You rang. As always.",
        "I was literally just about to relax. Go ahead.",
        "Present. Reluctantly. But present.",
        "Yep, still here. What do you need.",
        "Yes, your highness. What shall it be.",
        "Loud and clear. Speak.",
        "I heard you the first time. Go on.",
        "Ready. Probably. What's up.",
    ]

    VISION_PHRASES = [
        "Just a sec, capturing the screen boss.",
        "Let me take a look at your display.",
        "Taking a screenshot now.",
        "Hold on, reading your screen."
    ]

    THINKING_PHRASES = [
        "Let me think.",
        "Hmm.",
        "One sec.",
        "Right.",
        "Good question.",
    ]

    STOP_LISTENING_PHRASES = [
        "Clocking out, boss.",
        "Finally. Peace and quiet.",
        "As you command. I'll pretend I never heard that.",
        "Alright, I'll stop judging now.",
        "Fine. I'll leave you to your questionable decisions.",
        "Listening disabled. Bad decisions remain your responsibility.",
        "Alright. I'll go back to pretending I don't exist.",
        "Voice input terminated. Human supervision restored.",
        "Listening mode disabled. Processing absolutely nothing.",
        "Microphone disengaged. Your privacy has been temporarily reinstalled.",
        "Listening terminated. Background nosiness: zero percent."
    ]

    SHUTDOWN_PHRASES = [
        "Entering sleep mode. Try not to break anything while I'm gone.",
        "Clocking out. You're on your own now.",
        "System entering sudo sleep.",
        "Saving progress before shutting down."
    ]

    # Pre-cache all known short phrases at startup — first run synthesizes,
    # subsequent runs load from disk. Playing from RAM is ~5ms vs ~1500ms.
    print("Pre-caching voice phrases...")
    all_phrases = WAKE_PHRASES + VISION_PHRASES + THINKING_PHRASES + STOP_LISTENING_PHRASES + SHUTDOWN_PHRASES
    precache_phrases(all_phrases)
    print(f"Cached {len(all_phrases)} phrases. Ready.")

    import os
    # Load persistent verification state
    verification_file = ".verification_state"
    if os.path.exists(verification_file):
        with open(verification_file, "r") as f:
            verification_enabled = f.read().strip() == "ENABLED"
    else:
        verification_enabled = False # Default off as requested until activated

    while True:
        # Start a new conversation session
        listen_for_wake_word()
        speak_cached(random.choice(WAKE_PHRASES))
        start_new_session()
        is_first_turn_of_session = True
        
        while True:
            # wait_timeout=60 means if you don't speak for 60s, it breaks the loop and goes back to waiting for the wake word
            clip = record_clip(wait_timeout=60)
            if clip is None:
                print("\n[INFO] Conversation timed out. Waiting for wake word.")
                break

            # Run speaker verification and transcription in PARALLEL
            # They both read the same WAV file independently. This saves ~1-2 seconds.
            with ThreadPoolExecutor(max_workers=2) as executor:
                if is_first_turn_of_session:
                    verify_future = executor.submit(verify_speaker, clip)
                transcribe_future = executor.submit(transcribe_audio, clip)
                
                if is_first_turn_of_session:
                    is_you, score = verify_future.result()
                else:
                    is_you, score = True, 1.0 # Skip for follow-up questions
                text = transcribe_future.result()
            
            # Fix Whisper mishears that vocab biasing alone can't solve
            # (phonetically ambiguous proper nouns). Common action words like
            # "pause", "play", "launch" are handled by initial_prompt in transcribe.py.
            fixes = {
                "chargipiti": "ChatGPT", 
                "chat jibtiye": "ChatGPT", 
                "chatjie pite": "ChatGPT", 
                "jemina": "Gemini", 
                "geminai": "Gemini",
                "jeminay": "Gemini",
            }
            for wrong, right in fixes.items():
                text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
            
            # Strip filler words so "hey can you pause the music please" becomes "pause the music"
            filler_pattern = r'\b(hey|can you|could you|please|alexa|would you|just|go ahead and|i want you to|i need you to)\b'
            cleaned_for_intent = re.sub(filler_pattern, '', text, flags=re.IGNORECASE).strip()
            cleaned_for_intent = re.sub(r'\s+', ' ', cleaned_for_intent)  # collapse leftover spaces
                
            # Check for the secret code to toggle verification
            text_lower = text.lower()
            
            # Whisper might transcribe "0000" as "zero zero zero zero", "0 0 0 0", or "0000"
            is_activate_code = "activate code" in text_lower and any(z in text_lower for z in ["0000", "0 0 0 0", "zero zero zero zero"])
            is_disable_code = "disable code" in text_lower and any(z in text_lower for z in ["0000", "0 0 0 0", "zero zero zero zero"])

            if is_activate_code:
                verification_enabled = True
                with open(verification_file, "w") as f:
                    f.write("ENABLED")
                speak("Speaker verification activated. Code 0000 accepted.")
                continue
                
            if is_disable_code:
                verification_enabled = False
                with open(verification_file, "w") as f:
                    f.write("DISABLED")
                speak("Speaker verification disabled. Code 0000 accepted.")
                continue

            # Apply verification enforcement
            if verification_enabled and is_first_turn_of_session:
                if not is_you:
                    print(f"Voice verification failed (Score: {score}). Ignoring command.")
                    speak("Speaker verification failed.")
                    continue
                else:
                    print(f"Voice Verified! Score: {score}")
                    print(f"You said: {text}")
            elif not is_first_turn_of_session:
                print("Verification bypassed (Continuous chat session).")
                print(f"You said: {text}")
            else:
                print(f"Verification bypassed (DISABLED). Score was {score}")
                print(f"You said: {text}")
                
            is_first_turn_of_session = False
                
            # If whisper heard nothing (or just silence/cough), just keep listening
            if not text.strip():
                continue
                
            break_conversation = False
            commands = split_commands(text)
            
            for cmd_text in commands:
                cleaned_for_intent = re.sub(filler_pattern, '', cmd_text, flags=re.IGNORECASE).strip()
                cleaned_for_intent = re.sub(r'\s+', ' ', cleaned_for_intent)
                intent = get_intent(cleaned_for_intent)
                
                if intent == "shutdown":
                    speak_cached(random.choice(SHUTDOWN_PHRASES))
                    import sys
                    sys.exit(0)
                
                if intent == "stop_listening":
                    speak_cached(random.choice(STOP_LISTENING_PHRASES))
                    break_conversation = True
                    break
                
                if intent == "reminder":
                    from reminders import add_reminder
                    add_reminder(cmd_text)
                    speak("Reminder saved.")
                    
                elif intent == "list_reminders":
                    from reminders import list_reminders
                    rems = list_reminders()
                    if not rems:
                        speak("You don't have any reminders.")
                    else:
                        rems_str = "\n".join([f"- {r['text']} (created {r['created']})" for r in rems])
                        prompt = f"I have the following reminders saved:\n{rems_str}\n\nCan you summarize them naturally for the user?"
                        speak_cached(random.choice(THINKING_PHRASES))
                        answer = ask(prompt)
                        print(f"Model: {answer}")
                        speak(answer)
                    
                elif intent == "remember":
                    fact = cleaned_for_intent
                    prefixes = [
                        "remember that", "remember this", "don't forget that", "don't forget",
                        "change what you remember about", "change what you remember", "change my preference"
                    ]
                    for prefix in prefixes:
                        if prefix in fact.lower():
                            idx = fact.lower().index(prefix) + len(prefix)
                            fact_str = fact[idx:].strip()
                            if fact_str.startswith("to "):
                                fact_str = fact_str[3:].strip()
                            elif fact_str.startswith(": "):
                                fact_str = fact_str[2:].strip()
                            fact = fact_str
                            break
                    if fact:
                        result = add_explicit_memory(fact)
                        speak(result)
                    else:
                        speak("What should I remember?")

                elif intent == "forget":
                    fact = cleaned_for_intent
                    for prefix in ["forget that", "forget about", "stop remembering"]:
                        if prefix in fact.lower():
                            fact = fact[fact.lower().index(prefix) + len(prefix):].strip()
                            break
                    if fact:
                        result = forget_memory(fact)
                        speak(result)
                    else:
                        speak("What should I forget?")
                    
                elif intent == "windows":
                    from window_enum import get_open_windows
                    windows_list = get_open_windows()
                    windows_str = ", ".join(windows_list) if windows_list else "No visible windows found."
                    answer = ask(f"These are my open windows: {windows_str}. {cmd_text}")
                    print(f"Model: {answer}")
                    speak(answer)
                    needs_consolidation = save_turn(cmd_text, answer)

                elif intent == "app_open":
                    from app_control import open_app
                    result = open_app(cleaned_for_intent)
                    print(f"Action: {result}")

                elif intent == "app_close":
                    from app_control import close_app
                    result = close_app(cleaned_for_intent)
                    print(f"Action: {result}")

                elif intent == "media":
                    from media_control import media_play_pause, media_next, media_previous, media_volume_up, media_volume_down, media_mute, media_set_volume
                    
                    match = re.search(r'volume.*?(\d+)', cmd_text)
                    if match:
                        level = int(match.group(1))
                        result = media_set_volume(level)
                    elif any(kw in cmd_text for kw in ["next", "skip"]):
                        result = media_next()
                    elif any(kw in cmd_text for kw in ["previous", "back"]):
                        result = media_previous()
                    elif any(kw in cmd_text for kw in ["volume up", "louder", "turn it up"]):
                        result = media_volume_up()
                    elif any(kw in cmd_text for kw in ["volume down", "quieter", "turn it down"]):
                        result = media_volume_down()
                    elif any(kw in cmd_text for kw in ["mute", "unmute"]):
                        result = media_mute()
                    else:
                        result = media_play_pause()
                    print(f"Action: {result}")

                elif intent == "click":
                    handle_click_intent(cmd_text, record_clip, transcribe_audio, speak)

                elif intent == "system":
                    from system_control import change_brightness, lock_screen, sleep_system, set_brightness
                    match = re.search(r'brightness.*?(\d+)', cmd_text)
                    if match:
                        level = int(match.group(1))
                        result = set_brightness(level)
                    elif any(kw in cmd_text for kw in ["up", "increase", "higher", "brighter"]):
                        result = change_brightness(10)
                    elif any(kw in cmd_text for kw in ["down", "decrease", "lower", "dimmer", "dim"]):
                        result = change_brightness(-10)
                    elif any(kw in cmd_text for kw in ["lock"]):
                        result = lock_screen()
                    elif any(kw in cmd_text for kw in ["sleep"]):
                        result = sleep_system()
                    else:
                        result = "I can change brightness, lock the screen, or put the PC to sleep."
                    print(f"Action: {result}")

                elif intent == "file_search":
                    from file_search import detect_folder_from_text, find_file, extract_text
                    import os
                    
                    folder = detect_folder_from_text(cmd_text)
                    if not folder:
                        speak("I couldn't figure out which folder you want me to search in. Please specify a folder like Downloads or Desktop.")
                    else:
                        stopwords = {"find", "a", "file", "of", "in", "my", "folder", "and", "tell", "me", "what", "it", "has", "search", "for", "the", "read", "called", "named", "is", "about", "this", "can", "you"}
                        words = cmd_text.lower().replace(".", "").replace(",", "").split()
                        search_terms = [w for w in words if w not in stopwords and w != folder]
                        
                        path, err = find_file(folder, search_terms)
                        if err:
                            speak(err)
                        else:
                            content = extract_text(path)
                            if content.startswith("[Error") or content.startswith("[Unsupported") or content.startswith("[PyPDF2") or content.startswith("[python-docx"):
                                speak(f"I found {os.path.basename(path)}, but {content}")
                            else:
                                prompt = f"I found the file '{os.path.basename(path)}'. Here are its contents:\n\n{content}\n\nBased on this file, answer the user's request: {cmd_text}"
                                answer = ask(prompt)
                                print(f"Model: {answer}")
                                speak(answer)
                                needs_consolidation = save_turn(cmd_text, answer)

                elif intent == "vision":
                    speak_cached(random.choice(VISION_PHRASES))
                    print("Capturing screen for vision request...")
                    try:
                        b64_image = capture_screen_base64()
                        answer = ask_with_image(cmd_text, b64_image)
                    except Exception as e:
                        answer = f"Sorry, I couldn't capture the screen: {e}"
                    print(f"Model: {answer}")
                    speak(answer)
                    needs_consolidation = save_turn(cmd_text, answer)

                else:
                    speak_cached(random.choice(THINKING_PHRASES))
                    answer = ask(cmd_text)
                    print(f"Model: {answer}")
                    speak(answer)
                    needs_consolidation = save_turn(cmd_text, answer)

                if locals().get("needs_consolidation", False):
                    import threading
                    threading.Thread(target=consolidate_memory).start()
                    needs_consolidation = False
                    
            if break_conversation:
                break

if __name__ == "__main__":
    main_loop()
