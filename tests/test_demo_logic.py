from __future__ import annotations

import random
import tempfile
import unittest
from pathlib import Path

from core.enums import Destination, HandlingTag, PackageKind
from entities.package import CargoPackage
from infrastructure.storage import HighScoreStore
from managers.score_manager import ScoreManager
from managers.spawn_manager import SpawnManager


class ScoreManagerTests(unittest.TestCase):
    def test_express_delivery_builds_combo_and_score(self) -> None:
        package = CargoPackage(
            package_id=1,
            destination=Destination.NORTHPORT,
            kind=PackageKind.STANDARD,
            tag=HandlingTag.EXPRESS,
            position=__import__("pygame").math.Vector2(0, 0),
            spawned_at=0.0,
        )
        score = ScoreManager()
        gained, labels = score.award_delivery(package, now=2.0, fragile_clean=True)
        self.assertGreaterEqual(gained, 150)
        self.assertEqual(score.combo, 1)
        self.assertIn("EXPRESS +50", labels)

    def test_wrong_delivery_resets_combo(self) -> None:
        score = ScoreManager(score=500, combo=12)
        score.wrong_delivery()
        self.assertEqual(score.combo, 0)
        self.assertEqual(score.score, 400)


class SpawnManagerTests(unittest.TestCase):
    def test_training_phase_only_spawns_standard_tag(self) -> None:
        manager = SpawnManager(random.Random(7))
        package = manager.spawn(now=0.0, phase_index=0, belt_y=355.0)
        self.assertEqual(package.tag, HandlingTag.NONE)
        self.assertIn(package.destination, tuple(Destination))


class HighScoreStoreTests(unittest.TestCase):
    def test_only_higher_score_is_saved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "score.json"
            store = HighScoreStore(path)
            self.assertEqual(store.load(), 0)
            self.assertEqual(store.save_if_higher(1000), 1000)
            self.assertEqual(store.save_if_higher(250), 1000)
            self.assertEqual(store.load(), 1000)


if __name__ == "__main__":
    unittest.main()
