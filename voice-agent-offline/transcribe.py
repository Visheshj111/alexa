import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import numpy as np
from faster_whisper import WhisperModel

# Use base.en on CPU with 4 threads for sub-350ms transcription
model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=4)

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
