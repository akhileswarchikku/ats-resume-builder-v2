@echo off
title ATS Resume v2 - Frontend (port 5174)

cd /d "D:\ATS_Resume_v2\frontend"
if errorlevel 1 (
    echo ERROR: Folder D:\ATS_Resume_v2\frontend not found
    pause
    exit /b 1
)

if not exist node_modules (
    echo Installing npm dependencies...
    npm install
    if errorlevel 1 (
        echo ERROR: npm install failed
        pause
        exit /b 1
    )
)

echo Starting frontend on http://localhost:5174
npm run dev -- --port 5174

pause
