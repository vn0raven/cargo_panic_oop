from __future__ import annotations

import argparse

from application.game import CargoPanicGame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cargo Panic: Night Shift playable demo")
    parser.add_argument("--seed", type=int, default=None, help="Use a deterministic package sequence")
    parser.add_argument("--headless", action="store_true", help="Create a hidden window for smoke testing")
    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Reserved compatibility flag. This demo is balanced for mouse input.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.webcam:
        print("Webcam mode is not bundled in this gameplay demo; starting mouse mode.")
    CargoPanicGame(seed=args.seed, headless=args.headless).run()


if __name__ == "__main__":
    main()
