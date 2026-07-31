[CmdletBinding()]
param(
    [string]$Repository = "https://github.com/vn0raven/cargo_panic_oop.git",
    [string]$Branch = "feature/ui-enhanced",
    [string]$CommitMessage = "feat: add UI-enhanced Cargo Panic experience"
)

$ErrorActionPreference = "Stop"
$SourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found. Install Git for Windows first."
}

$workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("cargo-panic-publish-" + [guid]::NewGuid().ToString("N"))
$clonePath = Join-Path $workspace "repo"
New-Item -ItemType Directory -Path $workspace | Out-Null

Write-Host "Cloning $Repository..."
git clone $Repository $clonePath
if ($LASTEXITCODE -ne 0) { throw "Repository clone failed." }

Set-Location $clonePath
git ls-remote --exit-code --heads origin "refs/heads/$Branch" | Out-Null
if ($LASTEXITCODE -eq 0) {
    $Branch = "$Branch-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-Host "Requested branch already exists; using $Branch instead."
}

git switch -c $Branch
if ($LASTEXITCODE -ne 0) { throw "Could not create branch $Branch." }

$copyItems = @(
    ".github",
    "cargo_panic",
    "packaging",
    "tests",
    ".gitignore",
    "CargoPanic.spec",
    "BUILD_NOTES.md",
    "README.md",
    "UI_CHANGELOG.md",
    "UPSTREAM_SOURCE.md",
    "build_exe.bat",
    "build_exe.ps1",
    "main.py",
    "pyproject.toml",
    "requirements-build.txt",
    "requirements-webcam.txt",
    "requirements.txt",
    "publish_ui_branch.bat",
    "publish_ui_branch.ps1",
    "run_mouse.bat",
    "run_mouse.sh",
    "run_webcam.bat",
    "run_webcam.sh",
    "setup_and_run_mouse.bat",
    "setup_and_run_webcam.bat"
)

Write-Host "Overlaying the UI-enhanced implementation..."
foreach ($item in $copyItems) {
    $source = Join-Path $SourceRoot $item
    if (-not (Test-Path $source)) { continue }
    $destination = Join-Path $clonePath $item
    if (Test-Path $source -PathType Container) {
        if (-not (Test-Path $destination)) {
            New-Item -ItemType Directory -Path $destination | Out-Null
        }
        Copy-Item (Join-Path $source "*") $destination -Recurse -Force
    } else {
        $parent = Split-Path -Parent $destination
        if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
        Copy-Item $source $destination -Force
    }
}

git add --all
$changes = git status --porcelain
if (-not $changes) {
    throw "No changes were detected after overlaying the enhanced source."
}

Write-Host "Files staged for commit:"
git status --short

git commit -m $CommitMessage
if ($LASTEXITCODE -ne 0) {
    throw "Commit failed. Configure git user.name and user.email, then retry."
}

Write-Host "Pushing $Branch..."
git push --set-upstream origin $Branch
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Push did not complete. The prepared clone was kept at:"
    Write-Host $clonePath
    Write-Host "Authenticate with GitHub, then run:"
    Write-Host "  git -C `"$clonePath`" push --set-upstream origin $Branch"
    exit 1
}

Write-Host ""
Write-Host "Pushed branch: $Branch"
Write-Host "Open the repository on GitHub and create a pull request into main."
