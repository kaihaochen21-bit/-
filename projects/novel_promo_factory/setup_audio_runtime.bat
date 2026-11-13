@echo off
setlocal
set "AUDIO_ROOT=%USERPROFILE%\.codex\audio_runtime"
where uv >nul 2>nul
if errorlevel 1 (
  echo 未找到 uv。请先安装 uv: https://docs.astral.sh/uv/
  pause
  exit /b 1
)
if not exist "%AUDIO_ROOT%" mkdir "%AUDIO_ROOT%"

uv python install 3.11
if errorlevel 1 goto :fail

echo [1/5] 准备 ACE-Step 1.5...
if not exist "%AUDIO_ROOT%\ACE-Step-1.5\.git" (
  git clone --depth 1 https://github.com/ace-step/ACE-Step-1.5.git "%AUDIO_ROOT%\ACE-Step-1.5"
  if errorlevel 1 goto :fail
)
cd /d "%AUDIO_ROOT%\ACE-Step-1.5"
if not exist ".venv\Scripts\python.exe" uv venv --python 3.12 .venv
uv pip install --python "%AUDIO_ROOT%\ACE-Step-1.5\.venv\Scripts\python.exe" torch==2.7.1+cu128 torchvision==0.22.1+cu128 torchaudio==2.7.1+cu128 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python "%AUDIO_ROOT%\ACE-Step-1.5\.venv\Scripts\python.exe" -r "%~dp0audio_services\requirements-ace-runtime.txt" --index-url https://mirrors.aliyun.com/pypi/simple
if errorlevel 1 goto :fail

echo [2/5] 下载 ACE-Step 主模型（体积较大，首次需要较长时间）...
"%AUDIO_ROOT%\ACE-Step-1.5\.venv\Scripts\python.exe" -m acestep.model_downloader
if errorlevel 1 echo ACE-Step 模型下载未完成，可稍后在该目录重新运行模型下载命令。

echo [3/5] 准备 MeloTTS...
if not exist "%AUDIO_ROOT%\MeloTTS\.git" (
  git clone --depth 1 https://github.com/myshell-ai/MeloTTS.git "%AUDIO_ROOT%\MeloTTS"
  if errorlevel 1 goto :fail
)
cd /d "%AUDIO_ROOT%\MeloTTS"
set "HF_ENDPOINT=https://hf-mirror.com"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
if not exist ".venv311\Scripts\python.exe" uv venv --python 3.11 .venv311
uv pip install --python "%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" torch==2.2.2 torchaudio==2.2.2 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python "%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple
uv pip install --python "%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" -e . --index-url https://mirrors.aliyun.com/pypi/simple
uv pip install --python "%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" fastapi uvicorn "setuptools<81" hf_xet --index-url https://mirrors.aliyun.com/pypi/simple
if errorlevel 1 goto :fail
"%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" "%~dp0audio_services\patch_melotts_runtime.py" "%AUDIO_ROOT%\MeloTTS"
if errorlevel 1 goto :fail

echo [4/5] 下载 MeloTTS 中文模型...
"%AUDIO_ROOT%\MeloTTS\.venv311\Scripts\python.exe" -c "from melo.api import TTS; m=TTS(language='ZH', device='cpu'); print('MeloTTS ZH ready')"
if errorlevel 1 echo MeloTTS 中文模型预下载失败，首次调用时会再次尝试。

echo [5/5] 完成。
echo 请把 Freesound API Key 写入项目 .env，然后运行 start_audio_services.bat。
pause
exit /b 0
:fail
echo 安装失败，请检查网络、磁盘空间和 Python/uv 环境。
pause
exit /b 1
