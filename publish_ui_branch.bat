@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0publish_ui_branch.ps1" %*
if errorlevel 1 (
  echo.
  echo Publish did not complete. Review the error above.
  pause
  exit /b 1
)
pause
