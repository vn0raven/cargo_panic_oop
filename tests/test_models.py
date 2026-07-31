from __future__ import annotations

import random
import unittest

from cargo_panic.constants import ATTRIBUTE_VALUES, DESTINATIONS
from cargo_panic.models import (
    ContractStats,
    ParcelAttributes,
    build_mapping,
    destination_for,
)


class MappingTests(unittest.TestCase):
    def test_mapping_is_one_to_one(self) -> None:
        mapping = build_mapping("COLOR", random.Random(7))
        self.assertEqual(set(mapping), set(ATTRIBUTE_VALUES["COLOR"]))
        self.assertEqual(set(mapping.values()), set(DESTINATIONS))

    def test_destination_uses_only_active_rule(self) -> None:
        attributes = ParcelAttributes("RED", "HEAVY", "CIRCLE", "FRAGILE")
        mapping = {"RED": "SHIP", "BLUE": "TRUCK", "GREEN": "PLANE", "GOLD": "INSPECTION"}
        self.assertEqual(destination_for(attributes, "COLOR", mapping), "SHIP")


class ScoreTests(unittest.TestCase):
    def test_combo_increases_correct_score(self) -> None:
        stats = ContractStats()
        first = stats.record_correct()
        second = stats.record_correct()
        self.assertGreater(second, first)
        self.assertEqual(stats.best_combo, 2)

    def test_wrong_resets_combo(self) -> None:
        stats = ContractStats()
        stats.record_correct()
        stats.record_wrong()
        self.assertEqual(stats.combo, 0)
        self.assertEqual(stats.correct, 1)
        self.assertEqual(stats.wrong, 1)


if __name__ == "__main__":
    unittest.main()
