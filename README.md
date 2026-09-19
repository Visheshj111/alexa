# Offline Autonomous Multimodal AI Agent

An offline, low-latency multimodal AI voice and computer control agent for Windows. It combines real-time voice processing, local LLM/Vision reasoning, computer vision, PowerShell terminal automation, screen control, persistent memory, and a local web interface.

All processing runs 100% locally on your machine with zero external cloud dependencies or telemetry.

---

##  Capabilities

###  1. Real-Time Voice Engine & Speech Interruption
- **Wake Word Recognition:** Continuous low-overhead listener powered by `openwakeword`.
- **In-Memory STT & Speech Synthesis:** Speech-to-text via `faster-whisper` and text-to-speech via `PiperVoice` running entirely in RAM.
- **Barge-In / Instant Interrupt:** Saying *"stop"* or speaking while the assistant is responding halts audio playback in **< 100ms** and re-opens active listening immediately.

###  2. OS Control & Terminal Automation
- **PowerShell Command Generation:** Translates natural language requests (*"find all PDF files"*, *"scan disk space"*, *"delete temporary logs"*) into PowerShell commands.
- **Safety Confirmation Gate:** Destructive operations (`Remove-Item`, `del`, `format`) trigger mandatory user confirmation before execution.
- **App & Media Management:** Launch, close, and control applications, volume, and playback.

###  3. Computer Vision & Screen Automation
- **Zero-Delay Element Clicking:** Captures display content, computes normalized UI element coordinates via vision models, and clicks target elements instantly without confirmation delays.
- **Screen Text Input & Prompt Refinement:** Refines rough spoken instructions into structured prompts and inputs them into active windows via fast clipboard hotkeys.

###  4. Remote Web Interface & Terminal Modes
- **Web Interface:** Built-in REST server (`web_server.py`) serving a responsive mobile web interface accessible over local WiFi at `http://<host-ip>:8080`.
- **Keyboard Terminal Mode:** CLI chat mode for text interaction without microphone input (`--chat` flag).

---

##  System Architecture

```text
┌────────────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
│  Microphone Ingest     ├─────►│ OpenWakeWord Listener   ├─────►│ Faster-Whisper STT     │
└────────────────────────┘      └─────────────────────────┘      └───────────┬────────────┘
                                                                             │
                                                                             ▼
┌────────────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
│ Piper Speech Synthesis ◄──────┤ Intent Router & Memory  ◄──────┤ Local Vision/LLM Engine│
└───────────┬────────────┘      └────────────┬────────────┘      │ (Qwen3-VL via LM Studio│
            │                                │                   └────────────────────────┘
            ▼                                ▼
┌────────────────────────┐      ┌─────────────────────────┐
│ Speaker Audio Output   │      │ OS Actuation Engine     │
└────────────────────────┘      │ (PowerShell / Screen)   │
                                └─────────────────────────┘
```

---

##  Project Structure

```text
voice-agent-offline/
├── main.py              # Main loop, intent routing, barge-in, & CLI chat loop
├── persona.py           # Core system prompts and mode definitions
├── terminal_exec.py     # PowerShell command synthesis and execution safety layer
├── screen_click.py      # Display capture scaling and cursor click execution
├── screen_type.py       # Clipboard text entry and prompt refinement engine
├── web_server.py        # Flask REST web server for remote mobile/browser access
├── ask_local.py         # Local LLM chat completion handler
├── ask_vision.py        # Screenshot vision and coordinate extraction
├── transcribe.py        # Faster-Whisper transcription wrapper
├── speak.py             # Piper TTS audio streaming and phrase cache
├── memory.py            # Long-term persistent memory management
├── app_control.py       # Application launch and process management
├── media_control.py     # Core audio volume and media controls
├── system_control.py    # Display brightness, lock, and power state management
├── file_search.py       # Local file search and document extraction
├── reminders.py         # Persistent local reminder store
├── start_alexa.bat      # Primary Windows startup script
├── start_web.bat        # Web server startup script
└── templates/
    └── chat.html        # Responsive web chat interface
```

---

##  Setup & Requirements

### Prerequisites

- **OS:** Windows 10 / 11 Workstation
- **Python:** Python 3.10+
- **LM Studio:** Running local inference server on `http://localhost:1234` with a supported model (e.g., `qwen/qwen3-vl-4b`).
- **Piper TTS:** `en_US-lessac-medium.onnx` voice model placed in the root folder.

### Running the Application

1. **Start Voice Assistant:**
   ```cmd
   voice-agent-offline\start_alexa.bat
   ```

2. **Start in Terminal Chat Mode:**
   ```cmd
   voice-agent-offline\start_alexa.bat --chat
   ```

3. **Start Mobile Web Interface:**
   ```cmd
   python voice-agent-offline/web_server.py
   ```
   Access `http://<your-ip>:8080` from any device on your local network.

---

##  Example Usage

| Category | Example Command | Action |
| :--- | :--- | :--- |
| **Screen Click** | *"Click proceed button"* | Finds UI element visually and clicks it. |
| **Prompt Input** | *"Write a prompt to enhance my dashboard"* | Refines spoken prompt and types into active editor. |
| **Terminal Action** | *"Find all PDF files in my documents"* | Executes PowerShell search and summarizes results. |
| **Web Navigation** | *"Open chrome then go to github.com"* | Launches browser and opens target URL. |
| **Barge-In Interrupt**| *"Stop"* | Immediately cuts speech playback and re-opens listening. |
| **Vision Inquiry** | *"Look at my screen and summarize this error"* | Inspects screen content and returns brief answer. |
