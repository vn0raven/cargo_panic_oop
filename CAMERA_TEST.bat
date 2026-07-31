@echo off
setlocal
cd /d "%~dp0"
set CAMERA_INDEX=0
if not "%~1"=="" set CAMERA_INDEX=%~1
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\dev.ps1" -Mode Camera -Camera %CAMERA_INDEX%
exit /b %errorlevel%
