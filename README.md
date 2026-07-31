# Cargo Panic — Runnable OOP Build

This corrected package opens the Pygame game window. The default launch mode uses the mouse and does not import MediaPipe or open a webcam.

## Windows: quickest start

1. Install Python 3.12 and enable **Add Python to PATH** during installation.
2. Extract the ZIP completely.
3. Double-click `setup_and_run_mouse.bat`.
4. Press `Space` or `Enter` on the title screen.
5. Hold the left mouse button over a parcel, drag it, and release it over a loading bay.

After the first setup, use `run_mouse.bat` for later launches.

## Windows: command line

Open PowerShell in this folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

If PowerShell blocks virtual-environment activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Webcam mode

Use Python 3.12. Install the optional webcam packages:

```powershell
python -m pip install -r requirements-webcam.txt
python main.py --webcam --model hand_landmarker.task
```

Use another camera index:

```powershell
python main.py --webcam --model hand_landmarker.task --camera 1
```

The model path is resolved relative to this project folder, so the included `hand_landmarker.task` works even when the terminal was opened elsewhere.

## Controls

- `Space` or `Enter`: continue through menus and reports.
- Left mouse button: grab, drag, and release a parcel.
- Closed hand: grab a parcel in webcam mode.
- Open hand: release a parcel in webcam mode.
- `R`: retry from a contract report.
- `Esc`: quit.

## Persistent tracking behavior

- A grabbed item is detached from conveyor ownership before player ownership begins.
- Brief webcam loss stores the item in `TRACKING_SUSPENDED` at its exact last position.
- When the same hand returns, it resumes control of the same item.
- A prolonged loss releases the item in place instead of assigning its Y coordinate back to the conveyor.
- An invalid manual drop enters `REATTACHING` and smoothly interpolates back to the belt.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Troubleshooting

### A console flashes and no game window appears

Run the command from a terminal so the error remains visible:

```powershell
python main.py
```

The most common cause is a missing Pygame installation:

```powershell
python -m pip install -r requirements.txt
```

### `python` is not recognized

Use:

```powershell
py -3.12 main.py
```

### The previous build prints `Item 1: ON_CONVEYOR...` and closes

That is the old architecture-only demo. Use the corrected ZIP containing this README and a `main.py` whose window title is **Cargo Panic — OOP Persistent Tracking Build**.
