@echo off
call C:\Users\akhil\anaconda3\Scripts\activate.bat LLM_GPU
cd /d "D:\Apply Jobs"
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
