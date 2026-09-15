# Alexa / Jarvis — Offline Autonomous Multimodal AI Agent

A 100% offline, ultra-low-latency multimodal AI assistant for Windows 11. It combines real-time voice recognition, streaming local LLM reasoning (Qwen3-VL), computer vision, PowerShell terminal automation, zero-delay screen control, persistent memory, and a mobile web interface.

> **Privacy First & Local Execution**: Built to run entirely offline on consumer hardware (Infinix GT Book — i5-12500H, 16GB RAM, RTX 3050 GPU). No cloud APIs, no data telemetry, no external dependencies.

---

## ⚡ Key Features

### 🎙️ 1. Zero-Latency Voice Engine & Instant Barge-In
- **Persistent Wake-Word Loop:** Powered by `openwakeword` listening continuously for `"alexa"`.
- **In-Memory Speech-to-Text:** `faster-whisper` (`base.en`) running entirely in RAM with VAD noise filtering and speech vocabulary biasing.
- **In-Memory TTS & Pre-Caching:** `PiperVoice` ONNX model streaming PCM directly to audio output. Pre-caches 40+ high-frequency phrases for instant acknowledgment.
- **Instant Barge-In / Interruption:** Saying *"stop"*, *"Alexa stop"*, *"shut up"*, or speaking over the assistant halts TTS audio playback in **< 100ms** and re-opens active listening.

### 🧠 2. Unified "Jarvis" Persona (`persona.py`)
- Single source of truth identity: intelligent, witty, concise, direct (Stark's JARVIS style).
- Zero conversational filler (*"Certainly!"*, *"As an AI..."*), zero markdown formatting in spoken output.
- 100% self-aware of system capabilities: hardware specs, vision tools, terminal access, and file memory.

### 💻 3. Natural Language Terminal & OS Autonomy (`terminal_exec.py`)
- Translates natural language requests (*"find all PDF files"*, *"scan disk space"*, *"delete file test.txt"*, *"start anti-gravity in repo X"*) into single-line PowerShell commands.
- **Dual Safety Gate:** Destructive actions (`Remove-Item`, `del`, `format`) are automatically flagged by LLM + Python and require explicit voice/terminal confirmation before execution.

### 🖱️ 4. Zero-Delay Screen Clicking & Prompt Typing (`screen_click.py`, `screen_type.py`)
- **Instant Click Execution:** Saying *"click proceed button"* or *"look at my screen and click person 1"* automatically cleans verbal prefixes, captures the screen, calculates normalized coordinates via `Qwen3-VL`, and clicks **immediately** with zero confirmation delay.
- **AI Prompt Refinement:** Spoken commands like *"write a prompt to enhance my dashboard page by looking at the repo"* are refined by the local LLM into structured, high-quality prompts.
- **Clipboard Typing Engine:** Pastes text into active windows or prompt boxes using system clipboard hotkeys (`ctrl+v`), ensuring 100x faster pasting with zero dropped characters.

### 🌐 5. Mobile & WiFi Web Interface (`web_server.py`)
- Flask HTTP REST server running on port `8080` (`0.0.0.0:8080`).
- Sleek glassmorphic dark-mode web chat interface ([chat.html](file:///c:/Vishesh/Docs/Repos/alexa/voice-agent-offline/templates/chat.html)) designed for smartphones and laptops on local WiFi.
- Access the assistant's brain, vision, terminal execution, and media control from your phone browser at `http://<laptop-ip>:8080`.

### 💬 6. Interactive Terminal Chat Mode
- Switch between voice and typed terminal modes seamlessly.
- Say *"switch to chat mode"* or run `start_alexa.bat --chat` for quiet/public environments. Type `voice mode` to return.

---

## 🏗️ System Architecture

```text
                                  ┌───────────────────────────┐
                                  │   Microphone Audio Stream │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │   OpenWakeWord ("alexa")  │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │  Faster-Whisper STT (RAM) │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │   Verbal Prefix Stripper  │
                                  │   & Intent Classifier     │
                                  └───────┬───┬───┬───┬───────┘
                                          │   │   │   │
             ┌────────────────────────────┘   │   │   └─────────────────────────────┐
             ▼                                ▼   ▼                                 ▼
   ┌────────────────────┐          ┌────────────────────┐               ┌───────────────────────┐
   │ Screen Click /     │          │ PowerShell         │               │ Qwen3-VL-4B           │
   │ Clipboard Typing   │          │ Execution Engine   │               │ (LM Studio GPU)       │
   │ pyautogui / mss    │          │ (Safety Gated)     │               └───────────┬───────────┘
   └─────────┬──────────┘          └──────────┬─────────┘                           │
             │                                │                                     │
             └────────────────────────┬───────┴─────────────────────────────────────┘
                                      ▼
                           ┌─────────────────────┐
                           │ Memory & Session    │
                           │ Store (JSON/SQLite) │
                           └──────────┬──────────┘
                                      │
                                      ▼
                           ┌─────────────────────┐      Barge-In Interrupt
                           │ Piper TTS Stream    │ ◄─────────────────────────┐
                           └──────────┬──────────┘                           │
                                      │                                      │
                                      ▼                                      │
                           ┌─────────────────────┐                 ┌─────────┴─────────┐
                           │ sounddevice Output  ├─────────────────► Voice Interrupt  │
                           └─────────────────────┘                 │ Energy Monitor    │
                                                                   └───────────────────┘
```

---

## 📁 Repository Structure

```text
voice-agent-offline/
├── main.py              # Central orchestrator loop, intent dispatch, barge-in, & chat loop
├── persona.py           # Unified identity, capabilities, system prompts across all modes
├── terminal_exec.py     # PowerShell command generation & safe execution sandbox
├── screen_click.py      # Screenshot scaling & instant screen click execution
├── screen_type.py       # Clipboard pasting engine & AI prompt refinement
├── web_server.py        # Flask REST web server for remote phone/browser access
├── ask_local.py         # Local LLM chat completion handler (LM Studio API)
├── ask_vision.py        # Qwen3-VL screenshot vision & coordinate extraction
├── transcribe.py        # In-memory Faster-Whisper transcription engine
├── speak.py             # In-memory Piper TTS synthesis stream & phrase caching
├── memory.py            # Long-term cognitive memory & background consolidation
├── app_control.py       # Windows application launch & termination
├── media_control.py     # Media playback, volume, and mute controls
├── system_control.py    # Windows display brightness, lock, and sleep controls
├── file_search.py       # Fast file indexer & document text extraction
├── reminders.py         # Local reminder store
├── speaker_verify.py    # Voice biometric verification
├── start_alexa.bat      # Primary launcher (supports --chat flag)
├── start_web.bat        # Remote web server launcher
└── templates/
    └── chat.html        # Glassmorphism dark-mode mobile chat web UI
```

---

## 🚀 Getting Started

### Prerequisites

1. **Operating System:** Windows 11 Workstation.
2. **Python:** Python 3.10+ installed locally.
3. **LM Studio:** Running `qwen/qwen3-vl-4b` on GPU with local server listening on `http://localhost:1234`.
4. **Piper TTS:** `en_US-lessac-medium.onnx` voice model in the root project directory.

### Quick Start

1. **Launch Voice Agent:**
   Double-click `start_alexa.bat` or run in terminal:
   ```cmd
   c:\Vishesh\Docs\Repos\alexa\voice-agent-offline\start_alexa.bat
   ```

2. **Launch Terminal Chat Mode:**
   ```cmd
   start_alexa.bat --chat
   ```

3. **Launch Mobile Web Server:**
   Double-click `start_web.bat` or run:
   ```cmd
   python voice-agent-offline/web_server.py
   ```
   Open `http://<your-laptop-ip>:8080` from your phone or browser connected to the same local WiFi network.

---

## 🗣️ Example Commands

| Intent | Spoken / Typed Command | Action Taken |
| :--- | :--- | :--- |
| **Instant Click** | *"Alexa, click proceed button"* | Captures screen, calculates coordinates, clicks UI element immediately (<0.8s). |
| **Prompt Typing** | *"Alexa, write a prompt to enhance my dashboard page"* | Refines prompt using LLM, pastes into active window via `ctrl+v`. |
| **Terminal Search** | *"Alexa, find all PDF files in my documents"* | Executes `Get-ChildItem -Path ...` in PowerShell, speaks summary. |
| **Chained Action** | *"Alexa, open chrome then click person 1 and go to facebook.com"* | Opens Chrome, clicks profile button, navigates to website sequentially. |
| **Barge-In Stop** | *"Alexa, stop"* or *"Shut up"* | Instantly interrupts speech output, opens microphone for next command. |
| **Vision Analysis** | *"Alexa, look at my screen and tell me what error is showing"* | Ingests live display into `Qwen3-VL-4B`, returns brief solution. |
| **Chat Mode** | *"Alexa, switch to chat mode"* | Switches to typed keyboard terminal (`Alexa> `). |

---

## 🔒 Safety & Control Design

- **Zero Unsanitized Execution:** Destructive terminal actions (`Remove-Item`, `format`, `del`) are double-checked by Python safety functions and require explicit confirmation.
- **Zero Cloud Leakage:** All inference runs on your local GPU via LM Studio and PyTorch/ONNX runtimes.
- **Local Network Isolation:** The web server binds to `0.0.0.0:8080` for local WiFi devices only.

---

## 📄 License

Private repository developed for local workstation automation.
