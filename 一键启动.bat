@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "API_PORT=8000"
set "WEB_PORT=3000"

echo ==========================================
echo ReflexLearn 一键启动
echo ==========================================
echo 项目目录: %ROOT%
echo.

if not exist "%ROOT%.env" (
  echo [init] 未找到 .env，正在从 .env.example 复制...
  copy "%ROOT%.env.example" "%ROOT%.env" >nul
)

if not exist "%ROOT%frontend\.env.local" (
  echo [init] 未找到 frontend\.env.local，正在从 frontend\.env.example 复制...
  copy "%ROOT%frontend\.env.example" "%ROOT%frontend\.env.local" >nul
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='%ROOT%frontend\.env.local';" ^
  "$text=Get-Content -LiteralPath $p -Raw;" ^
  "$text=$text -replace 'BACKEND_ORIGIN=.*','BACKEND_ORIGIN=http://127.0.0.1:%API_PORT%';" ^
  "Set-Content -LiteralPath $p -Value $text -Encoding UTF8"

if not exist "%ROOT%.venv\Scripts\uvicorn.exe" (
  echo [error] 缺少后端依赖: .venv\Scripts\uvicorn.exe
  echo 请确认压缩包完整，或参考 STARTUP.md 重新安装后端依赖。
  pause
  exit /b 1
)

if not exist "%ROOT%frontend\node_modules\.bin\next.cmd" (
  echo [error] 缺少 Web 前端依赖: frontend\node_modules
  echo 请确认压缩包完整，或参考 STARTUP.md 重新安装前端依赖。
  pause
  exit /b 1
)

if not exist "%ROOT%uniapp\node_modules\.bin\uni.cmd" (
  echo [error] 缺少 uniapp 依赖: uniapp\node_modules
  echo 请确认压缩包完整，或参考 STARTUP.md 重新安装 uniapp 依赖。
  pause
  exit /b 1
)

echo [start] 后端 API: http://127.0.0.1:%API_PORT%
start "ReflexLearn API" /D "%ROOT%" cmd /k "set PYTHONPATH=%ROOT%src&& .venv\Scripts\uvicorn.exe reflexlearn.main:app --host 127.0.0.1 --port %API_PORT%"

timeout /t 3 /nobreak >nul

echo [start] Web 前端: http://127.0.0.1:%WEB_PORT%
start "ReflexLearn Web" /D "%ROOT%frontend" cmd /k "npm.cmd run dev -- --hostname 127.0.0.1 --port %WEB_PORT%"

timeout /t 2 /nobreak >nul

echo [start] UniApp H5: 终端中会显示访问地址，通常为 http://localhost:5173
start "ReflexLearn UniApp H5" /D "%ROOT%uniapp" cmd /k "npm.cmd run dev:h5"

echo.
echo 已启动 3 个命令行窗口:
echo   1. 后端 API      http://127.0.0.1:%API_PORT%
echo   2. Web 前端      http://127.0.0.1:%WEB_PORT%
echo   3. UniApp H5     查看 UniApp 窗口输出地址
echo.
echo 默认账号:
echo   admin / reflexlearn-admin
echo.
echo 关闭项目: 直接关闭刚打开的 3 个命令行窗口即可。
echo.
pause
