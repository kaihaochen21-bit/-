@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\agentops.ps1" -Mode Start
set EXITCODE=%ERRORLEVEL%
if not "%EXITCODE%"=="0" echo.
if not "%EXITCODE%"=="0" echo AgentOps 退出码：%EXITCODE%
pause