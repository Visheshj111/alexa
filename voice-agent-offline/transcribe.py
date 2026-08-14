from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu", compute_type="int8")  # Running on CPU saves ~1GB VRAM for your LM Studio model

def transcribe_audio(filepath):
    segments, _ = model.transcribe(filepath)
    return " ".join(segment.text for segment in segments)
