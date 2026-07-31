[CmdletBinding()]
param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
. (Join-Path $PSScriptRoot "common.ps1")

try {
    $buildRoot = Join-Path $ProjectRoot ".build"
    $buildRequirements = @(
        (Join-Path $ProjectRoot "requirements.txt"),
        (Join-Path $PSScriptRoot "requirements-build.txt")
    )
    $python = New-PythonEnvironment `
        -EnvironmentPath (Join-Path $buildRoot "venv") `
        -RequirementsPaths $buildRequirements

    Ensure-HandModel -ProjectRoot $ProjectRoot | Out-Null

    if (-not $SkipTests) {
        Write-Host "Running tests..."
        & $python -m unittest discover -s tests -v
        if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    }

    Remove-Item (Join-Path $ProjectRoot "build") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $ProjectRoot "dist") -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "Building CargoPanic.exe..."
    & $python -m PyInstaller --clean --noconfirm (Join-Path $PSScriptRoot "packaging\CargoPanic.spec")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

    $releaseFolder = Join-Path $ProjectRoot "dist\CargoPanic"
    $executable = Join-Path $releaseFolder "CargoPanic.exe"
    if (-not (Test-Path $executable)) { throw "CargoPanic.exe was not created." }

    Write-Host "Running packaged smoke test..."
    $smoke = Start-Process -FilePath $executable -ArgumentList "--headless" -Wait -PassThru
    if ($smoke.ExitCode -ne 0) { throw "The packaged smoke test failed with code $($smoke.ExitCode)." }

    $quickStart = @"
CARGO PANIC

Run CargoPanic.exe.
Select INPUT: MOUSE on the main menu to switch webcam control on or off.

Webcam gestures:
- Closed hand: grab
- Open hand: release

Keep this entire folder together. The _internal folder contains required camera libraries.
"@
    Set-Content -Path (Join-Path $releaseFolder "README.txt") -Value $quickStart -Encoding utf8

    $hash = (Get-FileHash -Algorithm SHA256 $executable).Hash.ToLowerInvariant()
    Set-Content `
        -Path (Join-Path $releaseFolder "CargoPanic.exe.sha256") `
        -Value "$hash  CargoPanic.exe" `
        -Encoding ascii

    $zipPath = Join-Path $ProjectRoot "dist\CargoPanic-Windows-x64.zip"
    Compress-Archive -Path $releaseFolder -DestinationPath $zipPath -Force

    Write-Host ""
    Write-Host "Build complete:" -ForegroundColor Green
    Write-Host "  $executable"
    Write-Host "  $zipPath"
    Write-Host ""
    Write-Host "Distribute the ZIP or the complete CargoPanic folder, not the EXE by itself."
}
catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
