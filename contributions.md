# Contributing to Offline Autonomous AI Agent

Hey! Thanks for stopping by and taking an interest in contributing.

We're building an autonomous, private, ultra-responsive voice and multimodal assistant that lives right on your local Windows PC. No cloud telemetry, no subscription paywalls, and no waiting 5–8 seconds for an external server to decide what to say.

If you like building fast local software, working with audio pipelines, hacking on local vision-language models, or writing native OS automation, you're in the right place.

---

## The Core Philosophy: Speed is Feature #1

Before you write any code, here is the most important constraint of this codebase:

> **If the assistant takes 5 seconds to answer, conversational flow is dead.**  
> Every millisecond matters. We optimize relentlessly for perceived sub-second (< 800ms) Time-To-First-Audio from the moment the user stops speaking.

Whenever you propose a change or add a feature, ask yourself: *Does this slow down the conversational hot loop?*

### The Golden Rules:
1. **Zero Disk I/O during turns:** Microphone audio, speech-to-text buffers, and TTS audio must stay in RAM (`numpy` arrays / PCM byte buffers). Never write `.wav` files to disk during an active interaction.
2. **Zero Process Spawns:** Never invoke `subprocess.run(["python", "-m", "piper", ...])` or shell out to CLI tools in the hot path. Models and TTS engines stay resident in memory.
3. **Pipelined Streaming:** Text generation from local LLMs and audio synthesis from Piper must stream concurrently. We start synthesizing speech on sentence one—never wait for the full LLM completion.
4. **Offline First, Hybrid Second:** The core assistant must run 100% offline without any internet connection. Enhancements like TypeSafe AI's Jev model provide ultra-fast (~70ms) probabilistic routing, but must always gracefully fall back to local heuristics if the machine is disconnected.
5. **Safety Gates for Destructive Actions:** The assistant has deep system authority (PowerShell, file deletions, process management). Always ensure destructive actions require user confirmation before executing.

---

## System Overview

Here is how the pieces fit together:

```
[ Microphone ] ──► [ OpenWakeWord ] ──► [ Faster-Whisper (in RAM) ]
                                                   │
                                                   ▼
                                         [ Master Dispatcher ]
                                                   │
              ┌────────────────────────────────────┼──────────────────────────────────┐
              ▼                                    ▼                                  ▼
      [ Regex Fast-Path ]               [ TypeSafe Jev (System 1) ]        [ Local Qwen3-VL (System 2) ]
        (< 1ms exact)                     (70–150ms typed intent)           (Deep multimodal reasoning)
                                                   │
                                                   ▼
                                        [ Actuation / Output ]
                                                   │
                      ┌────────────────────────────┴────────────────────────────┐
                      ▼                                                         ▼
            [ Streaming Piper TTS ]                                  [ OS & Screen Actuator ]
             (Direct to speakers)                                     (PowerShell / PyAutoGUI)
```

- **Perception:** `openwakeword` + in-memory `faster-whisper` (`tiny.en` / `base.en`).
- **Cognitive Layer:** Fast heuristics (<1ms) -> TypeSafe AI Jev System One (~70ms) -> Local Qwen3-VL-4B via LM Studio (System Two).
- **Actuation Layer:** In-memory `PiperVoice` streaming audio + Windows OS control (PowerShell, media, brightness, mouse clicks).

---

## Setting Up Your Development Environment

### 1. Prerequisites
- **OS:** Windows 10 or 11 (the automation and audio layer targets Windows native APIs).
- **Python:** 3.10 to 3.12 (virtual environment strongly recommended).
- **LM Studio:** Downloaded and running locally at `http://localhost:1234/v1` with `qwen/qwen3-vl-4b` (or another vision-language model).
- **GPU (Recommended):** An NVIDIA GPU with at least 4–6GB VRAM for smooth local LLM inference.

### 2. Clone and Install
```powershell
git clone https://github.com/Visheshj111/alexa.git
cd alexa

# Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r voice-agent-offline/requirements.txt  # or install active packages: faster-whisper openwakeword sounddevice soundfile piper-tts typesafe-sdk pyautogui opencv-python flask requests
```

### 3. Voice Models
Place the Piper ONNX voice files in the root or `voice-agent-offline` directory:
- `en_US-lessac-medium.onnx`
- `en_US-lessac-medium.onnx.json`

### 4. Optional API Keys (`.env`)
If you want to work on or test the TypeSafe AI Jev router:
1. Copy `.env.example` to `.env`.
2. Add your `TYPESAFE_API_KEY=your_key_here`.

*(If you don't have a key, no problem—the system will run entirely on local regex rules).*

---

## How to Test Your Changes

Don't test by talking to your microphone for 3 hours straight—it's exhausting and slow. Use these developer shortcuts:

### 1. Keyboard Chat Mode (No Mic Required)
Test intent routing, LLM reasoning, and OS actuation purely through the terminal:
```powershell
cd voice-agent-offline
python main.py --chat
```

### 2. Test the TypeSafe AI Jev Router
Verify intent classification schemas without booting the audio pipeline:
```powershell
python test_jev_router.py
```

### 3. Test Individual Components in Isolation
Each module can be tested independently:
```powershell
# Test TTS speech generation and latency
python voice-agent-offline/speak.py

# Test local LLM streaming responses
python voice-agent-offline/ask_local.py

# Test screen coordinate clicking
python voice-agent-offline/screen_click.py
```

### 4. Full Voice Agent Run
When you are ready to test end-to-end voice:
```powershell
.\start_alexa.bat
```

---

## Great Places to Contribute

Looking for inspiration? Here are areas where contributions are very welcome:

- **Acoustic Echo Cancellation (AEC) & True Duplex Barge-in:**  
  Currently, software barge-in can trip over its own speaker output if headphones aren't used. Writing or integrating a lightweight, in-memory AEC filter so users can interrupt the assistant without headphones would be massive.
- **Computer Vision & Screen Grounding:**  
  Improving coordinate normalization, multi-monitor display selection, and high-DPI scaling accuracy.
- **Intent Classification & Jev Schemas:**  
  Expanding the intent criteria in [`voice-agent-offline/typesafe_router.py`](file:///c:/Vishesh/Docs/Repos/alexa/voice-agent-offline/typesafe_router.py) to cover more everyday desktop workflows.
- **Windows OS Actuation:**  
  Adding smooth controls for virtual desktops, monitor switching, default audio device selection, or native Windows notification alerts.
- **Cognitive Memory & Context Pruning:**  
  Designing efficient SQLite or lightweight vector indexing for user preferences that doesn't blow the LLM's context window.
- **Cross-Platform Modularity:**  
  Abstracting the Windows-specific calls (`win32gui`, PowerShell) so Linux and macOS hackers can join the party.

---

## Coding Conventions & Expectations

We like simple, readable code that solves real problems without over-engineering:

- **Don't add massive dependencies for trivial tasks:** If a standard library module or a 10-line helper can do it, avoid adding an external package.
- **Keep the console clean:** Use clear logging prefixes like `[AUDIO]`, `[JEV]`, `[VISION]`, `[ACTION]` so developers can track the execution pipeline easily.
- **Handle errors gracefully:** Never let a failed intent lookup, broken network socket, or missing audio device crash the main loop. Catch errors, log a helpful message, and keep running.
- **Git Commits:** Keep them concise and descriptive. Conventional commit prefixes (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`) are encouraged.

---

## Submitting a Pull Request

1. **Fork the repo** and create a feature branch (`git checkout -b feat/ultra-fast-aec`).
2. **Make your changes** and test them locally.
3. **Verify compilation:**
   ```powershell
   python -m py_compile voice-agent-offline/*.py
   ```
4. **Push your branch** to your fork and open a Pull Request against `main`.
5. **Describe your changes:** Tell us what problem you solved, what testing you did, and include latency numbers if your PR touches the audio or inference path!

---

## Questions or Feedback?

Have a crazy idea or unsure how to approach something?  
Open an issue or start a discussion. We're friendly, pragmatic, and excited to see what you build!

