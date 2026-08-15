import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # Suppresses Intel MKL duplicate lib warning on Windows
from faster_whisper import WhisperModel

# CUDA fails at inference time (missing cublas64_12.dll from CUDA Toolkit, not just drivers).
# Forcing CPU. cpu_threads=4 prevents MKL from over-allocating and crashing with mkl_malloc.
model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)

# Vocabulary bias prompt — Whisper's decoder uses this to strongly prefer these words
# over phonetically similar alternatives. This replaces the need for hundreds of
# manual "paws" -> "pause" corrections. Add any word Whisper keeps getting wrong.
VOCAB_PROMPT = (
    "pause play skip next previous volume mute unmute louder quieter "
    "open launch start close "
    "chrome brave edge firefox vscode notepad discord spotify steam "
    "word excel powerpoint outlook notion gimp "
    "calculator settings wifi bluetooth display "
    "brightness lock screen sleep "
    "click press tap select "
    "remind me reminder "
    "ChatGPT Gemini "
    "screen looking at read this see this "
)

def transcribe_audio(filepath):
    segments, _ = model.transcribe(filepath, initial_prompt=VOCAB_PROMPT, vad_filter=True)
    return " ".join(segment.text for segment in segments)
