@echo off
cd /d %~dp0
D:\python\Python310\python.exe -m uvicorn main:app --reload --port 8000