@echo off
echo Starting LM Studio Server...
:: start /b runs the server in the background
start /b lms server start

:: Wait a few seconds for the server to spin up
timeout /t 5 /nobreak > NUL

echo Loading model into memory...
:: We default to loading gemma-4-12b. 
:: If you want the vision model, change this to: lms load qwen/qwen3-vl-4b
lms load google/gemma-4-12b-qat

echo LM Studio is ready!
