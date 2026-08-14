from wake_word import listen_for_wake_word
from speaker_verify import verify_speaker
from transcribe import transcribe_audio
from ask_local import ask
from speak import speak
from reminders import add_reminder
from screenshot import capture_screen_base64
from ask_vision import ask_with_image
from window_enum import get_open_windows
import sounddevice as sd
import soundfile as sf

import numpy as np
import time
import random

def get_intent(text):
    text = text.lower()
    if text.startswith("remind me"):
        return "reminder"
    if any(kw in text for kw in ["screen", "looking at", "read this", "see this", "on my display"]):
        return "vision"
    if any(kw in text for kw in ["open apps", "open windows", "what's open", "running right now", "list windows"]):
        return "windows"
    return "text"

def record_clip(filename="clip.wav", silence_limit=2.0, max_seconds=15):
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

    while True:
        listen_for_wake_word()
        speak(random.choice(WAKE_PHRASES))
        clip = record_clip()

        is_you, score = verify_speaker(clip)
        text = transcribe_audio(clip)
        
        # Hardcode fixes for common Whisper mishears
        import re
        fixes = {
            "chargipiti": "ChatGPT", 
            "chat jibtiye": "ChatGPT", 
            "chatjie pite": "ChatGPT", 
            "jemina": "Gemini", 
            "geminai": "Gemini",
            "jeminay": "Gemini"
        }
        for wrong, right in fixes.items():
            text = re.sub(re.escape(wrong), right, text, flags=re.IGNORECASE)
            
        if not is_you:
            print(f"Voice verification failed (Score: {score}), but bypassing it for now for testing!")
            print(f"I heard: {text}")
        else:
            print(f"Voice Verified! Score: {score}")
            print(f"You said: {text}")
        intent = get_intent(text)
        
        if intent == "reminder":
            add_reminder(text)
            speak("Reminder saved.")
            continue
        elif intent == "vision":
            phrases = [
                "Just a sec, capturing the screen boss.",
                "Let me take a look at your display.",
                "Taking a screenshot now.",
                "Hold on, reading your screen."
            ]
            speak(random.choice(phrases))
            print("Capturing screen for vision request...")
            try:
                b64_image = capture_screen_base64()
                answer = ask_with_image(text, b64_image)
            except Exception as e:
                answer = f"Sorry, I couldn't capture the screen: {e}"
        elif intent == "windows":
            print("Enumerating windows...")
            windows = get_open_windows()
            windows_list = ", ".join(windows) if windows else "No visible windows found."
            context_prompt = f"The user asked about their open windows. Here is the list of currently open window titles: {windows_list}. User's query: {text}"
            answer = ask(context_prompt)
        else:
            # Brief thinking phrase so there's no dead silence while the LLM generates
            thinking_phrases = [
                "Let me think.",
                "Hmm.",
                "One sec.",
                "Right.",
                "Good question.",
            ]
            speak(random.choice(thinking_phrases))
            answer = ask(text)
            
        print(f"Model: {answer}")
        speak(answer)

if __name__ == "__main__":
    main_loop()
