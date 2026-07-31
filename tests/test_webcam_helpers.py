from __future__ import annotations

import unittest
from dataclasses import dataclass

from cargo_panic.webcam import classify_hand_pose, palm_cursor


@dataclass
class Landmark:
    x: float
    y: float


def make_landmarks(open_hand: bool) -> list[Landmark]:
    points = [Landmark(0.5, 0.8) for _ in range(21)]
    points[0] = Landmark(0.50, 0.82)
    for index, x in zip((5, 9, 13, 17), (0.38, 0.46, 0.54, 0.62), strict=True):
        points[index] = Landmark(x, 0.62)
    for pip, tip, x in ((6, 8, 0.38), (10, 12, 0.46), (14, 16, 0.54), (18, 20, 0.62)):
        points[pip] = Landmark(x, 0.48)
        points[tip] = Landmark(x, 0.22 if open_hand else 0.68)
    return points


class WebcamHelperTests(unittest.TestCase):
    def test_open_hand(self) -> None:
        self.assertEqual(classify_hand_pose(make_landmarks(True)), "OPEN")

    def test_closed_hand(self) -> None:
        self.assertEqual(classify_hand_pose(make_landmarks(False)), "CLOSED")

    def test_cursor_uses_palm(self) -> None:
        x, y = palm_cursor(make_landmarks(True))
        self.assertAlmostEqual(x, 0.5, places=2)
        self.assertGreater(y, 0.6)


if __name__ == "__main__":
    unittest.main()
