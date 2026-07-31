$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "The virtual environment is missing. Running first-time setup..."
    & (Join-Path $PSScriptRoot "setup_and_run_mouse.ps1")
    exit $LASTEXITCODE
}

& $venvPython main.py
