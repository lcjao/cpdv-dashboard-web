@echo off
chcp 65001 >nul
setlocal EnableExtensions
title CPDV Dashboard Launcher

REM ============================================================
REM  CPDV Dashboard 一键启动 (start_all.bat)
REM  1) 定位 Python / Node   2) 安装依赖
REM  3) 同步算法代码索引      4) 清旧进程
REM  5) 起后端 8765          6) 起前端 5173
REM  7) 端口诊断 + 打开浏览器
REM  可选参数: start_all.bat [python路径] [node路径]
REM ============================================================

set "ROOT=%~dp0"
if "%~1"=="" (
  for %%P in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe" "C:\Python310\python.exe" "D:\python\cpdv-venv\Scripts\python.exe" "D:\App\Anaconda3\python.exe") do (
    if not defined PY if exist "%%~P" set "PY=%%~P"
  )
) else set "PY=%~1"
if "%~2"=="" (
  for %%N in ("%LOCALAPPDATA%\openclaw-bundle\node\node.exe" "D:\python\pythonProject\Node_js\node.exe") do (
    if not defined NODE if exist "%%~N" set "NODE=%%~N"
  )
) else set "NODE=%~2"

echo ============================================================
echo   CPDV Dashboard 一键启动
echo   项目根目录: %ROOT%
echo ============================================================
echo.

if not defined PY echo [错误] 未找到 Python，请: start_all.bat "C:\...\python.exe"
if not defined NODE echo [错误] 未找到 Node，请: start_all.bat "" "C:\...\node.exe"
if not defined PY exit /b 1
if not defined NODE exit /b 1
echo [0/7] Python = %PY%
echo       Node   = %NODE%
echo.

cd /d "%ROOT%"

echo [1/7] 后端依赖 (backend\requirements.txt)...
"%PY%" -m pip install --disable-pip-version-check -q -r backend\requirements.txt || echo [警告] pip install 失败，若已装依赖可忽略
echo.

echo [2/7] 前端依赖 (npm install)...
for %%I in ("%NODE%") do set "NODE_DIR=%%~dpI"
if exist "%NODE_DIR%npm.cmd" (
  call "%NODE_DIR%npm.cmd" install --no-fund --no-audit --prefix frontend >"%TEMP%\cpdv_npm_install.log" 2>&1
) else (
  "%NODE%" "%NODE_DIR%node_modules\npm\bin\npm-cli.js" install --no-fund --no-audit --prefix frontend >"%TEMP%\cpdv_npm_install.log" 2>&1
)
if errorlevel 1 echo [警告] npm install 失败（可检查 node_modules 是否已存在）
echo.

echo [3/7] 同步算法代码索引 (scripts\sync_algorithm_code.py --full)...
"%PY%" scripts\sync_algorithm_code.py --full
if errorlevel 1 echo [警告] 同步失败，前端仍可启动（使用旧索引）
echo.

echo [4/7] 清理 8765/5173/5174/5175 旧监听...
powershell -NoProfile -Command "$p=8765,5173,5174,5175;foreach($x in $p){$c=Get-NetTCPConnection -LocalPort $x -State Listen -EA SilentlyContinue;if($c){foreach($i in $c){try{Stop-Process -Id $i.OwningProcess -Force -EA SilentlyContinue}catch{}}}}" >nul 2>&1
timeout /t 1 /nobreak >nul
echo.

echo [5/7] 启动后端 (端口 8765, 新窗口)...
start "CPDV-Backend-8765" /D "%ROOT%\backend" cmd /k "%PY%" -m uvicorn main:app --host 127.0.0.1 --port 8765
echo.

echo [6/7] 启动前端 (端口 5173, 新窗口)...
start "CPDV-Frontend-5173" /D "%ROOT%\frontend" cmd /k "%ROOT%\start_frontend.bat" "%NODE%"
echo.

echo [7/7] 等待服务就绪并诊断端口...
timeout /t 6 /nobreak >nul
powershell -NoProfile -Command "$p=5173,5174,8765;foreach($x in $p){$c=Get-NetTCPConnection -LocalPort $x -State Listen -EA SilentlyContinue;if($c){Write-Host ('  端口 '+$x+' 已就绪 (PID '+$c[0].OwningProcess+')')}else{Write-Host ('  端口 '+$x+' 未就绪')}}";
echo.
echo   看板: http://localhost:5173
echo   API : http://127.0.0.1:8765/docs
echo   (若 5173 未就绪请查 5174；关闭后端/前端窗口即停止服务)
echo.
start "" cmd /c timeout /t 1 >nul && start http://localhost:5173
pause
endlocal
