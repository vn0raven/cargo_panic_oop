# Repository publishing and Windows build notes

## Prepared delivery

- `publish_ui_branch.ps1` clones the public repository, creates a non-destructive feature branch, overlays the UI-enhanced source, commits it, and pushes it using the local Git credential manager.
- `build_exe.ps1` creates an isolated Python 3.12 environment, installs Pygame and PyInstaller, runs tests, builds `dist\CargoPanic.exe`, smoke-tests it in headless mode, and writes a SHA-256 checksum.
- `.github/workflows/build-windows.yml` performs the same Windows build on GitHub-hosted Windows runners and uploads the executable, checksum, and ZIP as an Actions artifact.

## Validation performed in the sandbox

- Domain unit tests: passed.
- Python source compilation: passed.
- PyInstaller spec and Windows version-resource syntax parsing: passed.
- GitHub Actions workflow structure: parsed successfully.

## Environment limitation

The sandbox is Linux and has no authenticated GitHub write connection. It therefore cannot push to the repository or produce a genuine Windows `.exe`. PyInstaller builds for the operating system on which it is run, so the included Windows script or GitHub Actions workflow performs the final executable build.
