@echo off
chcp 65001 >nul
REM ============================================================
REM One-click launcher for CPDV dashboard (with algorithm sync)
REM   0) Sync algorithm code data
REM   1) clean stale listeners
REM   2) spawn backend
REM   3) spawn frontend
REM ============================================================

setlocal
set "ROOT=D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web"

echo ============================================================
echo   CPDV Dashboard - One-click launcher (with algorithm sync)
echo   Project root: %ROOT%
echo ============================================================
echo.

echo [0/4] Syncing algorithm code data (generating JSON for API)...
cd /d "%ROOT%"
call python scripts/sync_algorithm_code.py --full
if errorlevel 1 (
    echo.
    echo [ERROR] Algorithm sync failed! Check output above.
    echo Press any key to continue anyway...
    pause >nul
)
echo       done.
echo.

echo [1/4] Killing stale listeners + orphan node.exe ...
powershell -NoProfile -Command "$ports=5173,5174,5175,8765,8000; foreach($p in $ports){$c=Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue; if($c){foreach($x in $c){try{Stop-Process -Id $x.OwningProcess -Force -EA SilentlyContinue}catch{}}}}; foreach($n in Get-Process node -EA SilentlyContinue){try{Stop-Process -Id $n.Id -Force -EA SilentlyContinue}catch{}};" >nul 2>&1
timeout /t 1 /nobreak >nul
echo       done.
echo.

echo [2/4] Launching backend (new window: start_backend.bat) ...
start "CPDV-Backend-8765" /D "%ROOT%" cmd /k "%ROOT%\start_backend.bat"
echo.

echo [3/4] Launching frontend (new window: start_frontend.bat) ...
start "CPDV-Frontend-5173" /D "%ROOT%" cmd /k "%ROOT%\start_frontend.bat"
echo.

echo [4/4] Waiting for servers to start...
timeout /t 5 /nobreak >nul
echo.

echo ============================================================
echo   Three windows opened (sync done, backend, frontend).
echo   Browser: http://localhost:5173
echo   API:     http://127.0.0.1:8765/docs
echo ============================================================
echo.

powershell -NoProfile -Command "$ports=5173,8765; foreach($p in $ports){ $c=Get-NetTCPConnection -LocalPort $p -State Listen -EA SilentlyContinue; if($c){ Write-Host ('  PORT='+$p+' UP  PID='+$c.OwningProcess) } else { Write-Host ('  PORT='+$p+' DOWN <--- check corresponding window') } }"
echo.

echo Press any key to close this diagnostic window (DO NOT close backend/frontend windows).
echo [exit code %ERRORLEVEL%]
pause >nul
endlocal