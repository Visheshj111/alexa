
import subprocess
import os
import sounddevice as sd
import soundfile as sf
import re
import sys
import numpy as np

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
    # Convert smart apostrophes to standard straight apostrophes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    
    # Remove all types of quotes except apostrophes to keep contractions like "don't" intact
    text = re.sub(r'["`\u201c\u201d]', '', text)
    
    # Convert timestamps like 0:41, 3:57, 1:23:45 to speakable words BEFORE stripping colons
    text = re.sub(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b', _format_timestamp, text)

    # Convert "X / Y" timestamp pairs (e.g. "0:41 / 3:57") — the slash and surrounding
    # timestamps are already converted above; clean up the slash itself to "out of"
    text = re.sub(r'\(\s*(\d[\w\s]*?)\s*/\s*(\d[\w\s]*?)\s*\)', r'(\1 out of \2)', text)
    text = text.replace(' / ', ' out of ')
    
    # Collapse paragraph breaks into a natural spoken pause (full stop + space)
    text = re.sub(r'\n{2,}', '. ', text)
    # Collapse single newlines (often mid-list) into a comma pause
    text = re.sub(r'\n', ', ', text)

    # Remove bullet points and blockquotes at the start of lines
    text = re.sub(r'^\s*[-*+>]\s+', '', text, flags=re.MULTILINE)
    
    # Replace double dashes with a comma for a pause
    text = text.replace('--', ', ')
    
    # Keep only letters, numbers, whitespace, and basic punctuation (including apostrophes)
    # Everything else (emojis, math symbols, formatting characters) becomes a space
    text = re.sub(r'[^\w\s\.,!\?:;()\[\]\{}\']', ' ', text)
    
    # Collapse multiple spaces
    return re.sub(r'\s+', ' ', text).strip()

PIPER_MODEL = r"c:\Vishesh\Docs\Repos\alexa\en_US-lessac-high.onnx"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".phrase_cache")

def _piper_synthesize(text, wav_file):
    """Run Piper TTS on a text chunk and save to wav_file."""
    subprocess.run(
        [
            sys.executable, "-m", "piper",
            "--model", PIPER_MODEL,
            "--output_file", wav_file,
            "--length_scale", "1.15",   # ~15% slower = more conversational pacing
            "--noise_scale", "0.75",    # slight pitch/volume variation (less monotone)
            "--noise_w", "0.85",        # slight phoneme duration variation
        ],
        input=text.encode('utf-8', errors='ignore'),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def _play_wav(wav_file):
    """Play a wav file and delete it afterwards."""
    if os.path.exists(wav_file) and os.path.getsize(wav_file) > 0:
        try:
            data, fs = sf.read(wav_file)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            print(f"Audio playback error: {e}")

# ── Pre-cached phrase playback ──────────────────────────────────────────────
# Short phrases that we know at startup are pre-rendered once and cached as
# WAV files. Playing a cached WAV is ~5ms vs ~1500ms for a fresh Piper subprocess.

_phrase_audio_cache = {}  # phrase_text -> (numpy_array, sample_rate)

def _phrase_cache_path(phrase):
    """Deterministic filename for a cached phrase."""
    safe = re.sub(r'[^\w]', '_', phrase).strip('_')[:60]
    return os.path.join(CACHE_DIR, f"{safe}.wav")

def precache_phrases(phrases):
    """Pre-render a list of short phrases to WAV at startup. Only synthesizes
    phrases that aren't already cached on disk."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    for phrase in phrases:
        cache_file = _phrase_cache_path(phrase)
        if not os.path.exists(cache_file):
            _piper_synthesize(phrase, cache_file)
        # Load into memory for instant playback
        if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
            data, fs = sf.read(cache_file)
            _phrase_audio_cache[phrase] = (data, fs)

def speak_cached(phrase):
    """Play a pre-cached phrase instantly. Falls back to regular speak() if not cached."""
    if phrase in _phrase_audio_cache:
        data, fs = _phrase_audio_cache[phrase]
        sd.play(data, fs)
        sd.wait()
    else:
        speak(phrase)

def speak(text):
    text = clean_for_speech(text)
    if not text:
        return

    wav_file = "temp_response.wav"
    if os.path.exists(wav_file):
        try:
            os.remove(wav_file)
        except OSError:
            pass

    _piper_synthesize(text, wav_file)
    _play_wav(wav_file)
    # Clean up
    try:
        os.remove(wav_file)
    except OSError:
        pass
