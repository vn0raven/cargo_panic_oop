# Webcam integration boundary

The original Cargo Panic repository used a MediaPipe hand tracker. This demo keeps input handling concentrated in `application/game.py`, so webcam support can be restored without rewriting package, conveyor, scoring, or difficulty logic.

A webcam adapter should provide these normalized actions:

```text
pointer_position -> screen-space (x, y)
grab_started     -> equivalent to left mouse down
grab_held        -> update held package position
grab_released    -> equivalent to left mouse up
scan_held        -> equivalent to holding Space/right mouse
tracking_lost    -> release or suspend ownership safely
```

Recommended sequence:

1. Copy the original tracking worker and packet adapter into `infrastructure/vision/`.
2. Convert hand packets into the normalized actions above.
3. Add an input controller interface and separate mouse/webcam implementations.
4. Keep mouse mode as the balance and fallback reference.
5. Reintroduce `hand_landmarker.task` separately; it is not included in this ZIP.
