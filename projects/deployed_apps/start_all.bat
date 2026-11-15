@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_all.ps1" -OpenBrowser
if errorlevel 1 echo.
echo Press any key to close this window.
pause >nul
