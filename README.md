# Alexa — Local Voice & Computer Agent

#Alexa -- Local Voice & Computer Agent 

A local-first voice assistant for Windows that combines speech recognition, local LLM reasoning, persistent memory, computer vision, and deterministic PC automation.

> Built as a personal "Alexa for my PC" rather than a cloud-only chatbot: the assistant can understand spoken commands, answer questions with a local model, control applications and media, inspect the screen, search files, maintain memory, and execute computer actions with confirmation.

## What it can do

### Voice interaction
- Wake-word based conversation flow.
- Speech-to-text using Faster-Whisper.
- Natural text-to-speech using Piper, with pre-cached short responses for lower latency.
- Voice-session timeout and conversational turn handling.

### Local AI
- Uses an OpenAI-compatible local endpoint exposed by LM Studio for conversational reasoning.
- Keeps ordinary spoken answers concise and natural.
- Includes speech-to-text vocabulary biasing for common commands, applications, and technical terms.
- Handles phonetic speech-to-text mistakes through the assistant's system prompt.

### PC automation
- Open and close applications.
- Control media playback, volume, mute, and related actions.
- Enumerate open windows.
- Trigger Windows system actions such as brightness, lock, and sleep.
- Set and read reminders.
- Search and answer questions about files stored on the PC.

### Vision and computer use
- Capture the current screen and send it to a local vision-capable model.
- Ask questions about what is visible on the display.
- Locate UI elements from a screenshot and convert model coordinates into real screen coordinates.
- Require spoken confirmation before executing an inferred screen click.

### Persistent memory
- Stores conversation history separately from structured memory.
- Memory entries carry category, source, confidence, timestamps, and active/stale state.
- Explicit user memories are treated differently from inferred memories.
- LLMs propose memory changes; Python validates the proposal before modifying the memory store.
- Keeps a backup and changelog of memory changes.

### Voice verification
- Includes voice enrollment and speaker verification support so the assistant can distinguish an authorized speaker.

## Architecture

```text
                    ┌──────────────────────┐
                    │      Microphone      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Wake Word        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Faster-Whisper STT   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Intent Routing     │
                    └───────┬───────┬──────┘
                            │       │
             ┌──────────────┘       └─────────────────┐
             ▼                                        ▼
   ┌────────────────────┐                  ┌─────────────────────┐
   │ Deterministic      │                  │ Local LLM / Vision  │
   │ PC Tools           │                  │ via LM Studio       │
   │ apps, media, files │                  │ reasoning + vision  │
   │ reminders, system  │                  └──────────┬──────────┘
   └──────────┬─────────┘                             │
              │                                       │
              └──────────────────┬────────────────────┘
                                 ▼
                       ┌──────────────────────┐
                       │ Memory / Context     │
                       │ validated + stored   │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Piper Text-to-Speech │
                       └──────────┬───────────┘
                                  │
                                  ▼
                              Speaker
```

## Key engineering decisions

### Deterministic actions stay outside the LLM
The language model is used for reasoning and natural-language interaction, while actions such as opening applications, changing system state, searching files, or clicking the screen are handled by explicit Python tools. This keeps high-impact computer actions more controllable and testable.

### Memory uses a validation layer
The LLM does not directly rewrite `memory.json`. It proposes changes, and Python validates the structure and allowed categories before applying them. This reduces the chance of accidental or malformed memory updates.

### Confirmation before visual clicks
For screen-control commands, the vision model first identifies the target and coordinates. The agent then asks for spoken confirmation before performing the click.

### Latency-aware speech output
Known short phrases are synthesized once, cached to WAV, and loaded into memory. This avoids spawning a new TTS process for every wake/acknowledgement phrase.

## Project structure

```text
voice-agent-offline/
├── main.py              # Main assistant loop and intent routing
├── ask_local.py         # Local LLM requests through LM Studio
├── ask_vision.py        # Screenshot + vision-model interaction
├── transcribe.py        # Faster-Whisper transcription
├── speak.py             # Piper TTS and phrase caching
├── memory.py            # Persistent memory + consolidation/validation
├── app_control.py       # Application launch/close
├── media_control.py     # Media and volume controls
├── file_search.py       # File search and file-content workflows
├── screenshot.py        # Screen capture
├── screen_click.py      # Coordinate scaling and mouse execution
├── reminders.py         # Reminder support
├── speaker_verify.py    # Speaker verification
├── enroll_voice.py      # Voice enrollment
└── start_alexa.bat      # Windows launcher
```

## Example commands

```text
"Alexa, open VS Code."
"What apps are open?"
"Play some music and turn the volume down."
"Remind me to submit the assignment at 7 PM."
"Remember that I prefer concise answers."
"What do you remember about me?"
"Find the PDF about operating systems and tell me what's in it."
"What am I looking at on my screen?"
"Click the settings icon."
```

For actions that can affect the computer, the agent is designed to route the request through explicit tools rather than asking the LLM to freely execute arbitrary code.

## Local setup

The project is currently designed around a Windows environment.

### Prerequisites

- Python environment with the project's Python packages installed.
- A microphone and speakers/headphones.
- LM Studio running an OpenAI-compatible local chat endpoint on `localhost:1234`.
- A compatible local model for text reasoning and, where needed, vision input.
- Piper with the configured voice model for speech synthesis.
- A Windows desktop environment for the application/system automation modules.

### Run

1. Configure the local model in LM Studio.
2. Configure the local Piper voice model path used by `speak.py`.
3. Complete voice enrollment if speaker verification is enabled.
4. Start the assistant using `start_alexa.bat` or run `main.py` directly.
5. Wait for the wake-word listener, then speak a command.

## Design notes

This project intentionally mixes deterministic software engineering with local AI instead of treating everything as an LLM problem. The LLM provides language understanding, reasoning, memory proposals, and vision interpretation; Python owns the stateful application logic and system-level actions.

The result is a small experimental computer agent that sits between a traditional desktop automation tool and a modern multimodal AI assistant.

## Limitations

- The current implementation is Windows-specific in several areas, including application paths and system-control behavior.
- The local LLM/vision experience depends on the model loaded in LM Studio and the available hardware.
- Computer-use actions should be treated as an experimental automation layer and reviewed carefully before enabling unrestricted actions.
- Configuration is currently code-driven rather than packaged as a polished installer or cross-platform distribution.

## Tech stack

**Python · Faster-Whisper · LM Studio · Local LLMs · Local Vision · Piper TTS · sounddevice · soundfile · Windows automation · JSON-based persistent memory**

## Repository

[GitHub — VisheshJ111/alexa](https://github.com/Visheshj111/alexa)
