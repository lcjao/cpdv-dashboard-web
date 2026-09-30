@echo off
chcp 65001 >nul
REM ============================================================
REM Start backend only (uvicorn on port 8765)
REM Uses project venv: D:\python\cpdv-venv\Scripts\python.exe
REM Close this window to stop the server.
REM ============================================================

cd /d "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend"

echo ============================================================
echo   CPDV Backend - Port 8765
echo   venv: D:\python\cpdv-venv\Scripts\python.exe
echo   cmd : uvicorn main:app --host 127.0.0.1 --port 8765
echo   Close this window to stop.
echo ============================================================

"D:\python\cpdv-venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8765

echo.
echo [exit code %ERRORLEVEL%] Press any key to close
pause >nul