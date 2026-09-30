@echo off
cd /d %~dp0
D:\python\cpdv-venv\Scripts\python.exe -m uvicorn main:app --reload --port 8765
