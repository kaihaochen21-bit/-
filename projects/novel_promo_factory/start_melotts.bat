@echo off
setlocal
set "ROOT=%~dp0"
set "AUDIO_ROOT=%USERPROFILE%\.codex\audio_runtime"
if not exist "%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" (
  echo MeloTTS 运行时尚未安装。
  echo 请先运行 setup_audio_runtime.bat。
  pause
  exit /b 1
)
"%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" -c "import melo" >nul 2>nul
if errorlevel 1 (
  echo MeloTTS 依赖尚未安装完整。
  echo 请先运行 setup_audio_runtime.bat。
  pause
  exit /b 1
)
set "PYTHONPATH=%ROOT%;%AUDIO_ROOT%\MeloTTS;%PYTHONPATH%"
set "MELOTTS_DEVICE=auto"
set "HF_ENDPOINT=https://hf-mirror.com"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
cd /d "%AUDIO_ROOT%\MeloTTS"
start "MeloTTS API" cmd /k "%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" -m uvicorn audio_services.melotts_server:app --host 127.0.0.1 --port 8766
endlocal
