@echo off
chcp 65001 >nul
REM ============================================================
REM Start frontend only (Vite dev server, default port 5173)
REM Close this window to stop the server.
REM ============================================================

cd /d "D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend"

echo ============================================================
echo   CPDV Frontend - Vite dev server
echo   Default URL: http://localhost:5173
echo   Look for: [Vite Config] API_TARGET: http://127.0.0.1:8765
echo   Close this window to stop.
echo ============================================================

call npm run dev

echo.
echo [exit code %ERRORLEVEL%] Press any key to close
pause >nul