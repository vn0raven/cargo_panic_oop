@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\dev.ps1" -Mode Game
exit /b %errorlevel%
