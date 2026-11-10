@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating Python virtual environment...
  where py >nul 2>nul
  if %errorlevel%==0 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment creation failed.
  pause
  exit /b 1
)
if not exist ".venv\.deps_ok" (
  echo [2/3] Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
  if errorlevel 1 (
    echo Dependency installation failed. Check network or proxy.
    pause
    exit /b 1
  )
  type nul > ".venv\.deps_ok"
)
echo [3/3] Starting Novel Promo Factory...
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
".venv\Scripts\python.exe" run.py
pause