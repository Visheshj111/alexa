@echo off
REM Wait 30 seconds for LM Studio to fully load its model before starting the voice agent
timeout /t 30 /nobreak >nul

cd /d "c:\Vishesh\Docs\Repos\alexa\voice-agent-offline"

REM Check for --chat flag
if "%1"=="--chat" (
    echo Starting Alexa in Chat Mode...
    "C:\Users\vishe\AppData\Local\Python\bin\python.exe" main.py --chat
) else (
    echo Starting Alexa in Voice Mode...
    "C:\Users\vishe\AppData\Local\Python\bin\python.exe" main.py
)
