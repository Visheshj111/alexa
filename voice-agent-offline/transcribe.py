import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # Suppresses Intel MKL duplicate lib warning on Windows
from faster_whisper import WhisperModel

# CUDA fails at inference time (missing cublas64_12.dll from CUDA Toolkit, not just drivers).
# Forcing CPU. cpu_threads=4 prevents MKL from over-allocating and crashing with mkl_malloc.
model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=4)

def transcribe_audio(filepath):
    segments, _ = model.transcribe(filepath)
    return " ".join(segment.text for segment in segments)
