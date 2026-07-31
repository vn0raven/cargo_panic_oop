[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Resolve-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3.12")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($version -ne "3.12") {
            throw "Python 3.12 is required. Found Python $version."
        }
        return @("python")
    }
    throw "Python 3.12 was not found. Install it and enable 'Add Python to PATH'."
}

$launcher = @(Resolve-PythonLauncher)
$venvPython = Join-Path $ProjectRoot ".venv-build\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating isolated build environment..."
    $pythonCommand = $launcher[0]
    $pythonArgs = @($launcher | Select-Object -Skip 1)
    & $pythonCommand @pythonArgs -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

Write-Host "Installing build dependencies..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $venvPython -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Build dependency installation failed." }

if (-not $SkipTests) {
    Write-Host "Running unit tests..."
    & $venvPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Unit tests failed." }
}

Write-Host "Building CargoPanic.exe..."
& $venvPython -m PyInstaller --clean --noconfirm CargoPanic.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$exe = Join-Path $ProjectRoot "dist\CargoPanic.exe"
if (-not (Test-Path $exe)) {
    throw "PyInstaller completed without creating dist\CargoPanic.exe."
}

Write-Host "Running packaged headless smoke test..."
& $exe --headless
if ($LASTEXITCODE -ne 0) {
    throw "Packaged executable smoke test failed with exit code $LASTEXITCODE."
}

$hash = (Get-FileHash -Algorithm SHA256 $exe).Hash.ToLowerInvariant()
$hashLine = "$hash  CargoPanic.exe"
Set-Content -Path (Join-Path $ProjectRoot "dist\CargoPanic.exe.sha256") -Value $hashLine -Encoding ascii

Write-Host ""
Write-Host "Build complete: $exe"
Write-Host "SHA-256: $hash"
