# Local Voice Agent, Fully Offline Build Plan

Target machine: Infinix GT Book, i5-12500H, RTX 3050 6GB VRAM, 16GB DDR5
Wake word: "Alexa"
Requirement: zero internet dependency after initial setup, no exceptions, no license servers, no cloud calls ever

This replaces the earlier Porcupine plus Eagle plus Claude version. Those had two problems for a truly offline goal: Picovoice's SDK does an online license check on first use and periodically after, and Claude obviously needs internet by definition. Both are swapped out below for fully open source, fully local alternatives.

---

## 1. Architecture Overview

```
[Mic stream, always on]
        |
        v
[1. Wake word detector, openWakeWord]  <-- near zero CPU, fully local
        | (triggers only on "alexa")
        v
[2. Speaker verification, SpeechBrain ECAPA-TDNN]  <-- confirms it's YOUR voice
        | (only proceeds if match)
        v
[3. Speech to text, faster-whisper]  <-- transcribes what you said
        |
        v
[4. Local LLM, Ollama]  <-- gets the actual answer, no internet
        |
        v
[5. Text to speech, Piper]  <-- speaks the answer back
        |
        v
[6. Reminder handler, flat JSON file]  <-- runs in parallel
```

The honest caveat: every one of these tools downloads a pretrained model file once, either during pip install or on first run. That download needs internet. After that single download, the model is cached on disk and the tool never touches the network again, forever, regardless of how many times you restart your laptop or how long you stay offline. This is different from Picovoice, which validates a license key against their servers repeatedly over the tool's lifetime, not just once.

---

## 2. Tooling Choices, Fully Open Source

| Component | Tool | License model | Offline behavior |
|---|---|---|---|
| Wake word | openWakeWord | Fully open source, Apache 2.0 | Downloads pretrained models once on setup, zero network after |
| Speaker verification | SpeechBrain, ECAPA-TDNN model | Fully open source, Apache 2.0 | Downloads model once from Hugging Face on first run, zero network after |
| Speech to text | faster-whisper | Fully open source, MIT | Downloads model once, zero network after |
| LLM | Ollama, running Qwen2.5 or your existing Gemma setup | Fully open source runtime, models vary in license but run 100% local | Zero network ever once model is pulled |
| Text to speech | Piper | Fully open source, MIT | Downloads voice model once, zero network after |
| Reminders | Flat JSON file on disk | N/A | Zero network, always |

No component here phones home, checks a license server, or has any recurring network dependency. This is the airtight version.

---

## 3. Environment Setup

```bash
mkdir voice-agent-offline && cd voice-agent-offline
python -m venv venv
venv\Scripts\activate

pip install openwakeword pyaudio faster-whisper speechbrain torch torchaudio piper-tts numpy requests
```

Notes:
- `torch` and `torchaudio` are needed for SpeechBrain, if you already have them from other ML work on this laptop, pip will skip reinstalling
- `pyaudio` on Windows: if the install fails, run `pip install pipwin` then `pipwin install pyaudio`
- Ollama is a separate install, not a pip package, download it from ollama.com, then run `ollama pull qwen2.5:7b-instruct-q4_K_M` once while online
- No API keys needed anywhere in this version, no `.env` file required, nothing to sign up for

First run of the full pipeline needs internet once, to let openWakeWord, SpeechBrain, and faster-whisper each pull their model files. After that first run completes successfully, disconnect from WiFi and everything still works.

---

## 4. Project Structure

```
voice-agent-offline/
  main.py                     <- the always on loop
  wake_word.py                 <- step 1
  speaker_verify.py             <- step 2
  transcribe.py                  <- step 3
  ask_local.py                    <- step 4
  speak.py                         <- step 5
  reminders.py                      <- step 6
  enroll_voice.py                    <- one time script to record your reference voice sample
  enrolled_voice.wav                  <- generated after enrollment
  reminders.json                       <- flat file storage
```

---

## 5. Build Order

### Phase 1: Wake word detection, standalone

```python
# wake_word.py
import pyaudio
import numpy as np
from openwakeword.model import Model

def listen_for_wake_word():
    model = Model(wakeword_models=["alexa"])  # ships as a pretrained model, downloaded once on first use
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=16000,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=1280
    )

    print("Listening for wake word: alexa")
    try:
        while True:
            audio_chunk = np.frombuffer(stream.read(1280, exception_on_overflow=False), dtype=np.int16)
            prediction = model.predict(audio_chunk)
            if prediction["alexa"] > 0.5:
                print("Wake word detected.")
                return True
    finally:
        stream.close()
        pa.terminate()

if __name__ == "__main__":
    listen_for_wake_word()
```

Run this alone first. Say "Alexa" out loud, confirm it prints detected consistently before moving on. If it's too sensitive or misses too often, tune the `0.5` threshold up or down.

### Phase 2: Voice enrollment and speaker verification

Enrollment, one time, just records a clean reference sample:

```python
# enroll_voice.py
import pyaudio
import wave

def enroll(seconds=15, filename="enrolled_voice.wav"):
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)

    print("Speak naturally for 15 seconds. Read a paragraph out loud.")
    frames = [stream.read(1024) for _ in range(int(16000 / 1024 * seconds))]

    stream.stop_stream()
    stream.close()
    pa.terminate()

    wf = wave.open(filename, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b"".join(frames))
    wf.close()
    print(f"Saved reference voice sample to {filename}")

if __name__ == "__main__":
    enroll()
```

Verification, called after every wake word trigger, compares the new clip against your saved reference:

```python
# speaker_verify.py
from speechbrain.inference.speaker import SpeakerRecognition

verification_model = SpeakerRecognition.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec-ecapa-voxceleb"
)  # downloads once on first call, cached locally after

def verify_speaker(clip_path, reference_path="enrolled_voice.wav"):
    score, prediction = verification_model.verify_files(reference_path, clip_path)
    return bool(prediction), float(score)
```

Test this deliberately: have someone else say "Alexa" after you've enrolled, confirm `prediction` comes back false for them. Say it yourself at a different volume or distance from the mic, confirm it still comes back true for you. If it's too strict or too loose, the model exposes a `threshold` parameter you can pass into `from_hparams` to tune it.

### Phase 3: Speech to text

```python
# transcribe.py
from faster_whisper import WhisperModel

model = WhisperModel("small", device="cuda", compute_type="float16")  # uses your 3050, downloads once on first run

def transcribe_audio(filepath):
    segments, _ = model.transcribe(filepath)
    return " ".join(segment.text for segment in segments)
```

### Phase 4: Local LLM via Ollama

```python
# ask_local.py
import requests

def ask(question, model="qwen2.5:7b-instruct-q4_K_M"):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": question, "stream": False}
    )
    return response.json()["response"]
```

Ollama needs to be running in the background, `ollama serve`, before this call will work. No internet involved once the model has been pulled.

### Phase 5: Speak the answer

```python
# speak.py
import subprocess

def speak(text):
    subprocess.run([
        "piper",
        "--model", "en_US-lessac-medium.onnx",
        "--output-raw"
    ], input=text.encode(), stdout=subprocess.PIPE)
    # pipe stdout into an audio player, e.g. pyaudio or simpleaudio
```

Piper's binary and voice model file both need to be downloaded once from Piper's GitHub releases page, no pip package for the binary itself.

### Phase 6: Reminders

```python
# reminders.py
import json
import os
from datetime import datetime

FILE = "reminders.json"

def add_reminder(text, when=None):
    data = []
    if os.path.exists(FILE):
        with open(FILE) as f:
            data = json.load(f)
    data.append({"text": text, "created": str(datetime.now()), "when": when})
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

def list_reminders():
    if not os.path.exists(FILE):
        return []
    with open(FILE) as f:
        return json.load(f)
```

Stays pure disk I/O, no network component, no upgrade needed here unless you deliberately want calendar sync later, which would break the fully offline requirement for that one piece only.

### Phase 7: Wire it all together

```python
# main.py
from wake_word import listen_for_wake_word
from speaker_verify import verify_speaker
from transcribe import transcribe_audio
from ask_local import ask
from speak import speak
from reminders import add_reminder
import pyaudio
import wave

def record_clip(seconds=5, filename="clip.wav"):
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    frames = [stream.read(1024) for _ in range(int(16000 / 1024 * seconds))]
    stream.stop_stream()
    stream.close()
    pa.terminate()

    wf = wave.open(filename, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(pa.get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b"".join(frames))
    wf.close()
    return filename

def main_loop():
    while True:
        listen_for_wake_word()
        clip = record_clip()

        is_you, score = verify_speaker(clip)
        if not is_you:
            print(f"Voice not recognized, ignoring. Score: {score}")
            continue

        text = transcribe_audio(clip)
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
```

### Phase 8: Autostart and polish, optional, do this last

- Windows: Task Scheduler, run `main.py` at login, make sure `ollama serve` is also set to autostart or launches before your script does
- Watch VRAM: faster-whisper and Ollama's model both want GPU memory, on 6GB VRAM running both at once plus anything else GPU heavy will get tight, test this combination specifically before relying on it daily
- Add a simple state print or system tray indicator so you know when it's listening versus verifying versus thinking

---

## 6. Realistic Effort Breakdown

- Phase 1, wake word alone: half a day
- Phase 2, enrollment plus verification, including testing rejection with another voice: half a day
- Phase 3 to 5, STT, local LLM, TTS individually: half a day each
- Phase 6, reminders: an hour
- Phase 7, wiring together, debugging handoffs: a full day, this is where actual bugs live
- Phase 8, autostart, polish: whenever, not urgent

Total: a genuine weekend if focused, a week if spread around classes and Decision OS work.

## 7. Where This Will Actually Break

- First run needs internet for model downloads, don't test "fully offline" until after that first successful run, or it will just fail and you'll wrongly think something's broken
- Running Ollama's model and faster-whisper's model on GPU simultaneously will compete for your 6GB VRAM, if you hit memory errors, drop faster-whisper to `device="cpu"` and accept slightly slower transcription, or drop to a smaller Ollama model
- SpeechBrain's default threshold is tuned on a general dataset, not your specific voice and mic, expect to test and adjust it after the first few real attempts
- openWakeWord's "alexa" model was trained on general English speech patterns, if your accent or speaking style causes missed detections, lower the threshold in Phase 1 incrementally until it's reliable without being trigger happy on random background speech
- Piper's default voices sound robotic, that's expected for a fully local free voice, no fix for that without a heavier or paid model

Build in order, phase by phase, confirm each works standalone before wiring the next one in. Don't chain the whole pipeline before knowing each individual piece is solid.
