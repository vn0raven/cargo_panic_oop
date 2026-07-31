from __future__ import annotations

import argparse

from cargo_panic import CargoPanicGame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cargo Panic warehouse sorting game")
    parser.add_argument("--seed", type=int, default=None, help="Use a deterministic parcel sequence")
    parser.add_argument("--headless", action="store_true", help="Use SDL's hidden/dummy display for smoke tests")
    parser.add_argument("--webcam", action="store_true", help="Start optional MediaPipe webcam input")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index for webcam mode")
    parser.add_argument("--hand-model", default=None, help="Path to hand_landmarker.task")
    parser.add_argument("--preview", default=None, help="Save the first rendered frame to a PNG path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    game = CargoPanicGame(
        seed=args.seed,
        headless=args.headless,
        webcam=args.webcam,
        camera_index=args.camera,
        hand_model_path=args.hand_model,
        preview_path=args.preview,
    )
    game.run()


if __name__ == "__main__":
    main()
