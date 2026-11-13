@echo off
setlocal
set "ROOT=%~dp0"
set "AUDIO_ROOT=%USERPROFILE%\.codex\audio_runtime"
if not exist "%AUDIO_ROOT%\ACE-Step-1.5\.venv\Scripts\python.exe" (
  echo ACE-Step 运行时尚未安装。
  echo 请先运行 setup_audio_runtime.bat。
  pause
  exit /b 1
)
if not exist "%AUDIO_ROOT%\ACE-Step-1.5\.venv\Lib\site-packages\torch" (
  echo ACE-Step 依赖尚未安装完整。
  echo 请先运行 setup_audio_runtime.bat。
  pause
  exit /b 1
)
set "ACESTEP_OFFLOAD_TO_CPU=true"
set "ACESTEP_LM_BACKEND=pt"
set "ACESTEP_INIT_LLM=false"
cd /d "%AUDIO_ROOT%\ACE-Step-1.5"
start "ACE-Step API" cmd /k "%AUDIO_ROOT%\ACE-Step-1.5\.venv\Scripts\python.exe" -m acestep.api_server --host 127.0.0.1 --port 8001
endlocal
