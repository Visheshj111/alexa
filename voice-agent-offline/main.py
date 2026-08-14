from wake_word import listen_for_wake_word
from speaker_verify import verify_speaker
from transcribe import transcribe_audio
from ask_local import ask
from _soundfile import speak

from reminders import add_reminder
import sounddevice as sd
import soundfile as sf

import numpy as np
import time

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
    while True:
        listen_for_wake_word()
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

        if text.lower().startswith("remind me"):
            add_reminder(text)
            speak("Reminder saved.")
            continue

        answer = ask(text)
        print(f"Model: {answer}")
        speak(answer)

if __name__ == "__main__":
    main_loop()
