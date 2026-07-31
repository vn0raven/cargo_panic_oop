from __future__ import annotations

import argparse
import platform
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cargo_panic.webcam import WebcamHandInput, hand_model_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test Cargo Panic camera and hand tracking")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=8.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"Python: {sys.version.split()[0]} ({platform.architecture()[0]})")

    try:
        import cv2
        print(f"OpenCV: {cv2.__version__}")
    except Exception as exc:
        print(f"OpenCV import failed: {exc}")
        return 2

    try:
        import mediapipe as mp
        print(f"MediaPipe: {getattr(mp, '__version__', 'unknown')}")
    except Exception as exc:
        print(f"MediaPipe import failed: {exc}")
        return 2

    model = hand_model_path()
    print(f"Hand model: {model} ({'ready' if model.is_file() else 'missing'})")

    tracker = WebcamHandInput(args.camera)
    tracker.start()
    deadline = time.monotonic() + max(1.0, args.seconds)
    last_message = ""
    detected = False
    initialized = False
    failure = ""

    try:
        while time.monotonic() < deadline:
            snapshot = tracker.snapshot()
            if snapshot.message != last_message:
                print(snapshot.message)
                last_message = snapshot.message
            detected = detected or snapshot.detected
            initialized = initialized or tracker.available or bool(snapshot.backend)
            lower = snapshot.message.lower()
            if "error:" in lower or "unavailable" in lower or "missing" in lower:
                failure = snapshot.message
            time.sleep(0.1)
    finally:
        tracker.stop()

    if detected:
        print("Camera check passed: hand tracking is active.")
        return 0
    if initialized:
        print("Camera opened, but no hand was detected during the check.")
        print("Use even front lighting and keep the complete hand visible.")
        return 0

    print(failure or "Camera initialization failed.")
    print("Close other camera applications, then try camera index 1.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
