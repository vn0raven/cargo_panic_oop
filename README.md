# Cargo Panic

Cargo Panic is a Pygame warehouse-sorting game with mouse and webcam controls. Parcels move across a conveyor and must be routed to one of four destination bays using the active contract rule.

## Start from source on Windows

Double-click:

```text
START_GAME.bat
```

The first launch creates `.venv`, installs the runtime packages, and downloads the MediaPipe hand model. Later launches reuse that environment.

The game starts in mouse mode. Use the **INPUT: MOUSE** button on the main menu to enable webcam control.

## Webcam controls

- Closed hand: grab a parcel
- Open hand: release a parcel
- Mouse remains available as a fallback

Run `CAMERA_TEST.bat` to check camera 0. Run `CAMERA_TEST.bat 1` from Command Prompt to test camera 1.

## Build the Windows release

Double-click:

```text
BUILD_EXE.bat
```

Requirements:

- Windows 10 or 11, 64-bit
- Python 3.12, 64-bit
- Internet access for the first dependency and model download

Output:

```text
dist\CargoPanic\CargoPanic.exe
dist\CargoPanic-Windows-x64.zip
```

The webcam build is a PyInstaller **onedir** application. Keep `CargoPanic.exe` beside its `_internal` folder. Distribute the generated ZIP rather than copying the EXE alone.

## Development

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

Tests:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Headless render check:

```powershell
.venv\Scripts\python.exe main.py --headless --preview preview.png
```

## Project layout

```text
main.py                  Application entry point
cargo_panic/             Game logic, UI, models, and webcam adapter
tests/                   Logic and gesture tests
tools/                   Build, camera-check, and packaging internals
START_GAME.bat            Source launcher
CAMERA_TEST.bat           Camera diagnostic
BUILD_EXE.bat             Windows release builder
```

Modernized implementation based on the Cargo Panic project at `vn0raven/cargo_panic_oop`.
