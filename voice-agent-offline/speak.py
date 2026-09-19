import os
import re
import sys
import time
import numpy as np
import sounddevice as sd
from piper import PiperVoice

PIPER_MODEL = r"C:\Vishesh\Docs\Repos\alexa\en_US-lessac-medium.onnx"
if not os.path.exists(PIPER_MODEL):
    PIPER_MODEL = r"C:\Vishesh\Docs\Repos\alexa\en_US-lessac-high.onnx"

_voice_instance = None

def get_voice():
    """Get or lazily load the resident PiperVoice model in RAM."""
    global _voice_instance
    if _voice_instance is None:
        _voice_instance = PiperVoice.load(PIPER_MODEL)
    return _voice_instance

def _format_timestamp(m):
    """Convert MM:SS or H:MM:SS to speakable text."""
    parts = m.group(0).split(":")
    if len(parts) == 2:
        mins, secs = int(parts[0]), int(parts[1])
        hours = 0
    else:
        hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
    result = []
    if hours:
        result.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if mins:
        result.append(f"{mins} minute{'s' if mins != 1 else ''}")
    result.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " ".join(result)

def clean_for_speech(text):
    if not text:
        return ""
    # Convert smart apostrophes to standard straight apostrophes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    
    # Remove markdown asterisks, backticks, bold, italic
    text = re.sub(r'[*_`#~]', '', text)
    
    # Remove all types of quotes except apostrophes to keep contractions like "don't" intact
    text = re.sub(r'["\u201c\u201d]', '', text)
    
    # Convert timestamps like 0:41, 3:57, 1:23:45 to speakable words BEFORE stripping colons
    text = re.sub(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b', _format_timestamp, text)

    # Convert "X / Y" timestamp pairs (e.g. "0:41 / 3:57")
    text = re.sub(r'\(\s*(\d[\w\s]*?)\s*/\s*(\d[\w\s]*?)\s*\)', r'(\1 out of \2)', text)
    text = text.replace(' / ', ' out of ')
    
    # Collapse paragraph breaks into a natural spoken pause
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\n', ', ', text)

    # Remove bullet points and numbered lists at the start of lines
    text = re.sub(r'^\s*[-*+>]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Replace double dashes with a comma for a pause
    text = text.replace('--', ', ')
    
    # Keep only letters, numbers, whitespace, and basic punctuation
    text = re.sub(r"[^\w\s\.,!\?:;()\[\]\{}\']", ' ', text)
    
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', text).strip()

# ── Barge-in / interruption detection ───────────────────────────────────────
# During TTS playback, a parallel mic stream monitors for user speech.
# If the user speaks above the echo threshold, playback stops instantly.

_BARGE_IN_MIC_SR = 16000


ENABLE_BARGE_IN = os.environ.get("ENABLE_BARGE_IN", "1") == "1"

def _play_with_barge_in(audio_data, sample_rate):
    """Play audio with keyword-based barge-in detection.
    
    If you say 'Alexa' while the assistant is speaking, it will immediately stop.
    """
    if not ENABLE_BARGE_IN:
        sd.play(audio_data, sample_rate)
        sd.wait()
        return False

    mic_chunk = int(_BARGE_IN_MIC_SR * _BARGE_IN_CHECK_MS / 1000)
    duration = len(audio_data) / sample_rate
    
    # Start non-blocking playback
    sd.play(audio_data, sample_rate)
    
    try:
        from wake_word import _wake_model
        _wake_model.reset()
        
        # Open a 16000Hz int16 stream specifically for the wake word model
        with sd.InputStream(samplerate=16000, channels=1,
                            dtype='int16', blocksize=1280) as mic:
            
            # Flush the initial buffer to avoid immediate false positives from echo
            for _ in range(3):
                mic.read(1280)
                
            import time
            start_time = time.time()
            
            # Poll the microphone while the audio is still playing
            while time.time() - start_time < duration:
                audio_chunk, _ = mic.read(1280)
                audio_data = audio_chunk.flatten()
                prediction = _wake_model.predict(audio_data)
                
                if prediction.get("alexa", 0) > 0.5:
                    # User said "Alexa" — kill playback NOW
                    sd.stop()
                    print("[BARGE-IN] Wake word 'Alexa' detected. Stopping playback.")
                    return True
        
        # Playback finished naturally — make sure it's fully done
        sd.wait()
        return False
        
    except Exception as e:
        # If mic monitoring fails (e.g. no mic), fall back to normal playback
        try:
            sd.wait()
        except Exception:
            pass
        return False


# ── Pre-cached phrase playback ──────────────────────────────────────────────
_phrase_audio_cache = {}  # phrase_text -> (audio_float_array, sample_rate)

def precache_phrases(phrases):
    """Pre-synthesize short phrases directly into RAM at startup."""
    voice = get_voice()
    for phrase in phrases:
        if phrase not in _phrase_audio_cache:
            cleaned = clean_for_speech(phrase)
            if not cleaned:
                continue
            chunks = list(voice.synthesize(cleaned))
            if chunks:
                combined_audio = np.concatenate([c.audio_float_array for c in chunks])
                _phrase_audio_cache[phrase] = (combined_audio, chunks[0].sample_rate)

def speak_cached(phrase):
    """Play a pre-cached phrase instantly (<2ms). Falls back to speak() if not cached.
    No barge-in detection — cached phrases are short enough that interruption isn't needed."""
    if phrase in _phrase_audio_cache:
        data, fs = _phrase_audio_cache[phrase]
        sd.play(data, fs)
        sd.wait()
    else:
        speak(phrase)

def speak(text):
    """Direct in-memory synthesis and audio playback with barge-in detection.
    
    Returns:
        True if the user interrupted (barge-in detected), False otherwise.
    """
    text = clean_for_speech(text)
    if not text:
        return False
    voice = get_voice()
    for chunk in voice.synthesize(text):
        interrupted = _play_with_barge_in(chunk.audio_float_array, chunk.sample_rate)
        if interrupted:
            return True
    return False

def speak_stream(sentence_generator):
    """Pipelined streaming playback: speaks sentences as they are yielded by the LLM.
    
    Returns:
        tuple: (full_text: str, was_interrupted: bool)
    """
    full_text_list = []
    for sentence in sentence_generator:
        if not sentence:
            continue
        cleaned = clean_for_speech(sentence)
        if cleaned:
            full_text_list.append(cleaned)
            interrupted = speak(cleaned)
            if interrupted:
                return " ".join(full_text_list), True
    return " ".join(full_text_list), False

