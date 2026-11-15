@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_all.ps1"
echo Press any key to close this window.
pause >nul
