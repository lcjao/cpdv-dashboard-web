@echo off
chcp 65001 >nul
setlocal EnableExtensions
REM CPDV 前端启动器: npm run dev (Vite, 默认 5173, 被占则回退 5174)
REM 用法: start_frontend.bat [node路径]   — 不传则自动探测
set "ROOT=%~dp0.."

if "%~1"=="" (
  for %%N in ("%LOCALAPPDATA%\openclaw-bundle\node\node.exe" "D:\python\pythonProject\Node_js\node.exe" "C:\Program Files\nodejs\node.exe") do (
    if not defined NODE if exist "%%~N" set "NODE=%%~N"
  )
) else set "NODE=%~1"
if not defined NODE (
  echo [错误] 未找到 node，请: start_frontend.bat "C:\...\node.exe"
  exit /b 1
)

for %%I in ("%NODE%") do set "NODE_DIR=%%~dpI"
set "NPM_CMD=%NODE_DIR%npm.cmd"
if not exist "%NPM_CMD%" set "NPM_CMD=%NODE_DIR%node_modules\npm\bin\npm-cli.js"

cd /d "%ROOT%frontend"
echo   前端 dev server 启动中 (node: %NODE%  npm: %NPM_CMD%)
if exist "%NPM_CMD%" (
  call "%NPM_CMD%" run dev
) else (
  "%NODE%" "%NODE_DIR%node_modules\npm\bin\npm-cli.js" run dev
)
endlocal
