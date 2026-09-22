@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo Starting Alexa Web Server...
echo.

cd /d "%~dp0"
python web_server.py
