# Cargo Panic — UI Enhanced Fork

This folder is a clean UI-focused fork of the Cargo Panic warehouse-sorting game concept from:

- https://github.com/vn0raven/cargo_panic_oop

The sorting loop remains the same: inspect a parcel, use the active contract rule, drag it to one of four destination bays, and complete increasingly difficult batches.

## UI changes

- Clear three-level information hierarchy: active rule, routing map, then progress/score.
- Relevant parcel attribute is visually dominant; irrelevant metadata is quiet.
- Clickable controls on menus, briefings, pause, reports, and settings.
- Explicit valid/invalid drop states and reason-based error messages.
- Interactive practice shift with correct-bay guidance.
- Pause menu, accessibility settings, routing assist, high contrast, and reduced motion.
- Contract and campaign reports with quality, errors, score, and combo breakdowns.
- Optional webcam input with visible hand/tracking states and automatic mouse fallback.
- Keyboard focus navigation using Tab and Enter.

## Run with mouse

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## Run with webcam

```bash
python -m pip install -r requirements-webcam.txt
python main.py --webcam
```

Use another camera with `python main.py --webcam --camera 1`.

## Controls

- Left mouse: grab, carry, and release parcels.
- Closed hand: grab in webcam mode.
- Open hand: release in webcam mode.
- `Tab`: move focus between visible controls.
- `Enter` or `Space`: activate the focused control.
- `Esc` or `P`: pause/resume gameplay.
- `R`: restart the current contract.

## Tests

The domain tests do not require Pygame:

```bash
python -m unittest discover -s tests -v
```

A graphical smoke test can be run after installing Pygame:

```bash
python main.py --headless --preview preview.png
```

## Build a Windows `.exe`

PyInstaller must run on Windows to create a Windows executable. The repository includes a reproducible mouse-first build that creates one windowed file:

```powershell
.\build_exe.ps1
```

Or double-click `build_exe.bat`. The output is:

```text
dist\CargoPanic.exe
dist\CargoPanic.exe.sha256
```

The build uses Python 3.12, runs the domain tests, packages with `CargoPanic.spec`, and executes a headless smoke test against the finished executable. The standard build deliberately excludes OpenCV and MediaPipe, so it stays smaller and uses mouse input. Webcam packaging can be added as a separate, larger build target.

## Build through GitHub Actions

After this source is in GitHub:

1. Open **Actions**.
2. Select **Build Windows executable**.
3. Choose **Run workflow**.
4. Download the `CargoPanic-Windows-x64` artifact when the job completes.

Creating a tag such as `v1.1.0` also triggers the Windows build.

## Publish the UI branch

On a Windows machine with Git credentials configured, run:

```powershell
.\publish_ui_branch.ps1
```

The script clones the upstream repository, creates `feature/ui-enhanced`, overlays this implementation, commits it, and pushes the branch without modifying `main` directly. `publish_ui_branch.bat` is the double-click wrapper.
