from wake_word import listen_for_wake_word
from speaker_verify import verify_speaker
from transcribe import transcribe_audio
from ask_local import ask
from speak import speak, speak_cached, precache_phrases
from reminders import add_reminder
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
        
    # check BEFORE the generic "open" check below, since phrases like
    # "what apps are open" contain "open" but mean enumeration, not launching
    if any(kw in text for kw in ["open apps", "open windows", "what's open", "running right now", "list windows", "what apps"]):
        return "windows"

    if any(kw in text for kw in ["open ", "launch ", "start "]):
        return "app"

    if any(kw in text for kw in ["click", "press the", "tap the", "select the"]):
        return "click"

    if any(kw in text for kw in ["brightness", "lock screen", "lock the screen", "lock my pc", "lock my computer", "sleep", "go to sleep", "put the pc to sleep", "put the computer to sleep"]):
        return "system"

    if any(kw in text for kw in ["play", "pause", "skip", "next song", "previous song", "volume", "mute", "unmute", "louder", "quieter", "turn it up", "turn it down", "stop the music", "start the music"]):
        return "media"

    if any(kw in text for kw in ["screen", "looking at", "read this", "see this", "on my display", "what am i looking at"]):
        return "vision"

    return "text"

def record_clip(filename="clip.wav", silence_limit=1.5, max_seconds=15, seconds=None):
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
        f"Find the exact pixel location to click for: '{question}'. "
        f"Respond ONLY in this format: X,Y,DESCRIPTION "
        f"where X and Y are pixel coordinates in the image you were given, "
        f"and DESCRIPTION is a short label of what you're clicking."
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

    # Pre-cache all known short phrases at startup — first run synthesizes,
    # subsequent runs load from disk. Playing from RAM is ~5ms vs ~1500ms.
    print("Pre-caching voice phrases...")
    all_phrases = WAKE_PHRASES + VISION_PHRASES + THINKING_PHRASES
    precache_phrases(all_phrases)
    print(f"Cached {len(all_phrases)} phrases. Ready.")

    while True:
        listen_for_wake_word()
        speak_cached(random.choice(WAKE_PHRASES))
        clip = record_clip()

        # Run speaker verification and transcription in PARALLEL
        # They both read the same WAV file independently. This saves ~1-2 seconds.
        with ThreadPoolExecutor(max_workers=2) as executor:
            verify_future = executor.submit(verify_speaker, clip)
            transcribe_future = executor.submit(transcribe_audio, clip)
            is_you, score = verify_future.result()
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
            
        if not is_you:
            print(f"Voice verification failed (Score: {score}), but bypassing it for now for testing!")
            print(f"I heard: {text}")
        else:
            print(f"Voice Verified! Score: {score}")
            print(f"You said: {text}")
        intent = get_intent(cleaned_for_intent)
        
        if intent == "reminder":
            add_reminder(text)
            speak("Reminder saved.")
            
        elif intent == "windows":
            from window_enum import get_open_windows
            windows_list = get_open_windows()
            windows_str = ", ".join(windows_list) if windows_list else "No visible windows found."
            answer = ask(f"These are my open windows: {windows_str}. {text}")
            print(f"Model: {answer}")
            speak(answer)

        elif intent == "app":
            from app_control import open_app
            result = open_app(cleaned_for_intent)
            print(f"Action: {result}")

        elif intent == "media":
            from media_control import media_play_pause, media_next, media_previous, media_volume_up, media_volume_down, media_mute, media_set_volume
            
            # Check for absolute volume first (e.g. "volume to 50", "set volume to 20 percent")
            match = re.search(r'volume.*?(\d+)', text)
            if match:
                level = int(match.group(1))
                result = media_set_volume(level)
            elif any(kw in text for kw in ["next", "skip"]):
                result = media_next()
            elif any(kw in text for kw in ["previous", "back"]):
                result = media_previous()
            elif any(kw in text for kw in ["volume up", "louder", "turn it up"]):
                result = media_volume_up()
            elif any(kw in text for kw in ["volume down", "quieter", "turn it down"]):
                result = media_volume_down()
            elif any(kw in text for kw in ["mute", "unmute"]):
                result = media_mute()
            else:
                result = media_play_pause()
            print(f"Action: {result}")

        elif intent == "click":
            # Pass our local main.py functions as callbacks
            handle_click_intent(text, record_clip, transcribe_audio, speak)

        elif intent == "system":
            from system_control import change_brightness, lock_screen, sleep_system
            if any(kw in text for kw in ["up", "increase", "higher", "brighter"]):
                result = change_brightness(10)
            elif any(kw in text for kw in ["down", "decrease", "lower", "dimmer", "dim"]):
                result = change_brightness(-10)
            elif any(kw in text for kw in ["lock"]):
                result = lock_screen()
            elif any(kw in text for kw in ["sleep"]):
                result = sleep_system()
            else:
                result = "I can change brightness, lock the screen, or put the PC to sleep."
            print(f"Action: {result}")
            # we don't speak here either, just like media, so it's snappy

        elif intent == "vision":
            speak_cached(random.choice(VISION_PHRASES))
            print("Capturing screen for vision request...")
            try:
                b64_image = capture_screen_base64()
                answer = ask_with_image(text, b64_image)
            except Exception as e:
                answer = f"Sorry, I couldn't capture the screen: {e}"
            print(f"Model: {answer}")
            speak(answer)

        else:
            speak_cached(random.choice(THINKING_PHRASES))
            answer = ask(text)
            print(f"Model: {answer}")
            speak(answer)

if __name__ == "__main__":
    main_loop()
