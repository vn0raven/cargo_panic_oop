@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1" %*
if errorlevel 1 (
  echo.
  echo Build failed. Review the error above.
  pause
  exit /b 1
)
echo.
echo CargoPanic.exe is in the dist folder.
pause
