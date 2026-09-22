@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"

if "%1"=="--chat" (
    echo Starting Assistant in Chat Mode...
    python main.py --chat
) else (
    echo Starting Assistant in Voice Mode...
    python main.py
)
pause
