# Cargo Panic: Night Shift

A polished, mouse-first vertical slice built from the structure and interaction ideas in the original `vn0raven/cargo_panic_oop` project.

Packages travel across a live conveyor. Read their destination labels, prioritize urgent cargo, scan damaged labels, and drag each package into the correct shipping bay before the night shift collapses.

## Fastest Windows start

1. Extract the ZIP completely.
2. Install Python 3.12 and enable **Add Python to PATH**.
3. Double-click `setup_and_run_mouse.bat`.
4. Press Space or click on the title screen.

After the first setup, launch with `run_mouse.bat`.

## PowerShell start

```powershell
Set-Location "C:\path\to\cargo_panic_demo"
Set-ExecutionPolicy -Scope Process Bypass
.\setup_and_run_mouse.ps1
```

Manual setup:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Controls

- **Left mouse drag:** grab and route a package.
- **Space or right mouse:** hold while hovering a damaged package to scan its label.
- **Esc or P:** pause and resume.
- **R, Space, Enter, or click:** retry from the shift report.

## Demo systems

- Three readable destinations: Northport, Eastvale, and Westhaven.
- Five escalating phases lasting about five minutes in total.
- Standard, small, and heavy package bodies.
- Fragile, refrigerated, express, and damaged handling requirements.
- One-second damaged-label scanner interaction.
- Accuracy-first score, speed bonuses, combo multipliers, and three-strike pressure.
- Temporary bay closures, conveyor surges, and a final emergency mode.
- Procedural sound effects with no external asset downloads.
- Local high-score persistence.
- Results screen with accuracy, highest combo, average sort time, rank, and most common mistake.

## Package behavior

| Cargo property | Effect |
|---|---|
| Small | Moves slightly faster on the belt. |
| Heavy | Lags behind the cursor while dragged. |
| Fragile | Rough dragging costs points. |
| Refrigerated | Expires after roughly ten seconds. |
| Express | Pays a higher base score but has a visible urgency timer. |
| Damaged | Destination stays hidden until scanned. |

## Project structure

```text
application/        Pygame session and screen orchestration
core/               Configuration, phases, enums, shared events
entities/           Cargo package and player statistics models
interactables/      Conveyor, scanner, and shipping bays
managers/           Spawning, scoring, difficulty, and feedback
infrastructure/     Procedural audio and local score storage
tests/              Deterministic logic tests
main.py              Entry point
```

## Run tests

After setup:

```powershell
.\run_tests.ps1
```

Or directly:

```powershell
$env:SDL_VIDEODRIVER = "dummy"
$env:SDL_AUDIODRIVER = "dummy"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Webcam compatibility

The original repository included webcam and hand-tracking support. This vertical slice is intentionally balanced around reliable mouse input, and the `--webcam` flag currently falls back to mouse mode. See `WEBCAM_MIGRATION.md` for the clean integration boundary.

## Source base

Original repository: `https://github.com/vn0raven/cargo_panic_oop`

This ZIP is a gameplay-focused derivative prepared for the repository owner. It does not include the original MediaPipe model binary.
