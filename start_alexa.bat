@echo off
cd /d "%~dp0voice-agent-offline"

if "%1"=="--chat" (
    echo Starting Assistant in Chat Mode...
    python main.py --chat
) else (
    echo Starting Assistant in Voice Mode...
    python main.py
)
pause

