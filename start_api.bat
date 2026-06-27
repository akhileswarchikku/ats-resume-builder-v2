@echo off
title ATS Resume v2 - API (port 8002)

echo Activating LLM_GPU conda environment...
call C:\Users\akhil\anaconda3\Scripts\activate.bat LLM_GPU
if errorlevel 1 (
    echo ERROR: Failed to activate conda environment LLM_GPU
    pause
    exit /b 1
)

echo Starting API on http://localhost:8002
cd /d "D:\ATS_Resume_v2"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8002 --reload

pause
