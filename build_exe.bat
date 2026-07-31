@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo Build failed. Review the error above.
  pause
  exit /b 1
)
echo.
echo Windows release created in the dist folder.
pause
