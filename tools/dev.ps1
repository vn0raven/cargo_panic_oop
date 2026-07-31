[CmdletBinding()]
param(
    [ValidateSet("Game", "Camera")][string]$Mode = "Game",
    [int]$Camera = 0
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
. (Join-Path $PSScriptRoot "common.ps1")

try {
    $runtimeRequirements = @((Join-Path $ProjectRoot "requirements.txt"))
    $python = New-PythonEnvironment `
        -EnvironmentPath (Join-Path $ProjectRoot ".venv") `
        -RequirementsPaths $runtimeRequirements
    Ensure-HandModel -ProjectRoot $ProjectRoot | Out-Null

    if ($Mode -eq "Camera") {
        & $python (Join-Path $PSScriptRoot "camera_check.py") --camera $Camera --seconds 8
    }
    else {
        & $python (Join-Path $ProjectRoot "main.py")
    }

    if ($LASTEXITCODE -ne 0) { throw "$Mode exited with code $LASTEXITCODE." }
}
catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
