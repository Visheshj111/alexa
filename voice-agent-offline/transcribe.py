import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
import numpy as np
from faster_whisper import WhisperModel

# Use tiny.en with cpu_threads=2 for ultra-low latency and minimal memory footprint
model = WhisperModel("tiny.en", device="cpu", compute_type="int8", cpu_threads=2)

VOCAB_PROMPT = (
    "pause play skip next previous volume mute unmute louder quieter "
    "open launch start close "
    "chrome brave edge firefox vscode notepad discord spotify steam "
    "word excel powerpoint outlook notion gimp "
    "calculator settings wifi bluetooth display "
    "brightness lock screen sleep "
    "click press tap select "
    "remind me reminder "
    "remember forget what do you know about me "
    "activate code disable code "
    "search find file folder downloads documents desktop "
    "ChatGPT Gemini "
    "screen looking at read this see this "
)

def transcribe_audio(audio_source):
    """Transcribe audio from a file path or direct in-memory numpy array."""
    if isinstance(audio_source, np.ndarray):
        audio_data = audio_source.flatten()
        if audio_data.dtype == np.int16:
            audio_data = audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        segments, _ = model.transcribe(audio_data, initial_prompt=VOCAB_PROMPT, vad_filter=True)
    else:
        segments, _ = model.transcribe(audio_source, initial_prompt=VOCAB_PROMPT, vad_filter=True)
    return " ".join(segment.text for segment in segments).strip()
