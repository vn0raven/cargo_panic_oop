Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-Python312 {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @("py", "-3.12") }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $version = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($version -eq "3.12") { return @("python") }
    }

    throw "Python 3.12 (64-bit) is required. Install it from python.org and enable the Python launcher."
}

function New-PythonEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentPath,
        [Parameter(Mandatory = $true)][string[]]$RequirementsPaths
    )

    $python = Join-Path $EnvironmentPath "Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $launcher = @(Resolve-Python312)
        $command = $launcher[0]
        $arguments = @($launcher | Select-Object -Skip 1)
        & $command @arguments -m venv $EnvironmentPath | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
    }

    $hashInputs = [System.Collections.Generic.List[string]]::new()
    foreach ($requirementsPath in $RequirementsPaths) {
        $resolved = [System.IO.Path]::GetFullPath($requirementsPath)
        if (-not (Test-Path $resolved)) { throw "Requirements file not found: $resolved" }
        $hashInputs.Add($resolved)
    }
    $hashMaterial = foreach ($file in $hashInputs) {
        (Get-FileHash -Algorithm SHA256 $file).Hash.ToLowerInvariant()
    }
    $hashBytes = [Text.Encoding]::UTF8.GetBytes(($hashMaterial -join "|"))
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $requirementHash = ([BitConverter]::ToString($sha.ComputeHash($hashBytes))).Replace("-", "").ToLowerInvariant()
    }
    finally {
        $sha.Dispose()
    }
    $marker = Join-Path $EnvironmentPath ".requirements.sha256"
    $installedHash = if (Test-Path $marker) { (Get-Content $marker -Raw).Trim() } else { "" }

    if ($installedHash -ne $requirementHash) {
        & $python -m pip install --disable-pip-version-check --upgrade pip | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
        foreach ($requirementsPath in $RequirementsPaths) {
            & $python -m pip install --disable-pip-version-check -r $requirementsPath | Out-Host
            if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed for $requirementsPath." }
        }
        Set-Content -Path $marker -Value $requirementHash -Encoding ascii
    }

    return $python
}

function Ensure-HandModel {
    param([Parameter(Mandatory = $true)][string]$ProjectRoot)

    $destination = Join-Path $ProjectRoot "cargo_panic\assets\hand_landmarker.task"
    if ((Test-Path $destination) -and (Get-Item $destination).Length -gt 1000000) {
        return $destination
    }

    $url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    $folder = Split-Path -Parent $destination
    $temporary = "$destination.download"
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
    Remove-Item $temporary -Force -ErrorAction SilentlyContinue

    Write-Host "Downloading the MediaPipe hand model..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $temporary -UseBasicParsing
    }
    catch {
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            & curl.exe -L --fail --silent --show-error $url -o $temporary
            if ($LASTEXITCODE -ne 0) { throw }
        }
        else {
            throw
        }
    }

    if (-not (Test-Path $temporary) -or (Get-Item $temporary).Length -lt 1000000) {
        Remove-Item $temporary -Force -ErrorAction SilentlyContinue
        throw "The hand model download was incomplete. Check the internet connection and run again."
    }

    Move-Item $temporary $destination -Force
    return $destination
}
