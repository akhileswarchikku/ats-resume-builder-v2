@echo off
cd /d "D:\ATS_Resume_v2\frontend"
if not exist node_modules (
    echo Installing dependencies...
    npm install
)
npm run dev -- --port 5174
