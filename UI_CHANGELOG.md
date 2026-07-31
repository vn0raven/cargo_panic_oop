# UI/UX implementation notes

## Implemented

1. **Information hierarchy**
   - Active rule receives the strongest visual emphasis.
   - Routing map is always adjacent and uses icon/text/color redundancy.
   - Batch, pass threshold, score, combo, correct, wrong, and missed metrics are separated.

2. **Parcel readability**
   - Active attribute is displayed in a large central card.
   - Non-active attributes are reduced to quiet metadata.
   - Color, symbol, weight, and status each have a distinct visual treatment.

3. **Interaction feedback**
   - Grab selection has an explicit focus ring.
   - Hovered bays show success/error previews.
   - Tutorial and optional routing assist reveal the correct bay.
   - Invalid releases return smoothly to the conveyor.

4. **Error teaching**
   - Wrong drops state the parcel value and correct destination.
   - Missed parcels explain that the parcel exited before sorting.
   - Tracking loss preserves position and explains recovery/fallback.

5. **Navigation and recovery**
   - All major screens use visible buttons.
   - Keyboard focus, pause, restart, menu return, and settings are implemented.
   - Webcam dependency/camera failures do not block mouse play.

6. **Accessibility**
   - High-contrast mode.
   - Reduced-motion mode.
   - Routing assist.
   - Labels and symbols supplement color.

## Architecture

- `cargo_panic/models.py`: rule, parcel, scoring, and campaign domain logic.
- `cargo_panic/rendering.py`: reusable theme, button, panel, parcel, bay, and icon drawing.
- `cargo_panic/webcam.py`: optional background hand-tracking adapter.
- `cargo_panic/game.py`: screen flow, input handling, gameplay orchestration, and UI composition.

## Packaging and delivery

- Added a PyInstaller one-file/windowed build specification.
- Added Windows build and smoke-test scripts.
- Added a GitHub Actions workflow that produces a Windows x64 executable, ZIP, and SHA-256 checksum.
- Added a guarded publishing script that pushes the implementation to a feature branch rather than directly replacing `main`.
