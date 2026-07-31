from __future__ import annotations

import unittest

from application.game_world import GameWorld
from core.enums import ItemEventType, ItemState
from core.vector import Vec2
from entities.item import ItemAttributes, PackageItem
from entities.player import PlayerInteractor
from interactables.conveyor import LinearConveyor
from interactables.drop_zone import DropZone


class PersistentTrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.world = GameWorld()
        self.belt = LinearConveyor("belt-1", 347.0, 100.0, -200.0, 1400.0)
        self.world.add_conveyor(self.belt)
        self.player = PlayerInteractor("Left", Vec2(100.0, 347.0))
        self.world.add_player(self.player)
        self.item = PackageItem(
            entity_id=7,
            position=Vec2(100.0, 347.0),
            attributes=ItemAttributes("RED", "LIGHT", "CIRCLE", "NORMAL"),
        )
        self.world.spawn_on_conveyor(self.item, "belt-1", 0.0)

    def test_grab_detaches_item_from_conveyor(self) -> None:
        grabbed = self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        self.assertEqual(grabbed, 7)
        self.world.update(1.0, 1.1)
        snapshot = self.world.items.snapshot(7)
        self.assertEqual(snapshot.state, ItemState.HELD)
        self.assertEqual(snapshot.x, 100.0)
        self.assertNotIn(7, self.belt.attached_item_ids)

    def test_tracking_loss_preserves_exact_position(self) -> None:
        self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        held_position = Vec2(428.5, 221.25)
        self.world.interactions.update_pointer("Left", held_position, 0.2)
        self.world.interactions.tracking_lost("Left", 0.3)
        snapshot = self.world.items.snapshot(7)
        self.assertEqual(snapshot.state, ItemState.TRACKING_SUSPENDED)
        self.assertEqual((snapshot.x, snapshot.y), (held_position.x, held_position.y))

    def test_tracking_recovery_resumes_same_item(self) -> None:
        self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        self.world.interactions.update_pointer("Left", Vec2(400.0, 200.0), 0.2)
        self.world.interactions.tracking_lost("Left", 0.3)
        self.world.interactions.tracking_recovered("Left", Vec2(410.0, 205.0), 0.5)
        snapshot = self.world.items.snapshot(7)
        self.assertEqual(snapshot.state, ItemState.HELD)
        self.assertEqual(snapshot.holder_id, "Left")
        self.assertEqual((snapshot.x, snapshot.y), (410.0, 205.0))

    def test_long_tracking_loss_drops_in_place_not_on_belt(self) -> None:
        self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        position = Vec2(500.0, 180.0)
        self.world.interactions.update_pointer("Left", position, 0.2)
        self.world.interactions.tracking_lost("Left", 0.3)
        self.world.interactions.update(2.0)
        snapshot = self.world.items.snapshot(7)
        self.assertEqual(snapshot.state, ItemState.DROPPED)
        self.assertEqual((snapshot.x, snapshot.y), (500.0, 180.0))
        self.assertNotEqual(snapshot.y, self.belt.center_y)

    def test_invalid_release_reattaches_without_immediate_snap(self) -> None:
        self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        release = Vec2(600.0, 150.0)
        outcome = self.world.interactions.release(
            "Left",
            release,
            0.3,
            drop_zones=[],
            conveyors=self.world.conveyors,
        )
        self.assertEqual(outcome, ("reattaching", 7))
        snapshot = self.world.items.snapshot(7)
        self.assertEqual(snapshot.state, ItemState.REATTACHING)
        self.assertEqual((snapshot.x, snapshot.y), (600.0, 150.0))

        self.belt.update(self.world.items, 0.05, 0.35)
        mid = self.world.items.snapshot(7)
        self.assertGreater(mid.y, 150.0)
        self.assertLess(mid.y, self.belt.center_y)

    def test_grab_event_is_persisted(self) -> None:
        self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        event_types = [event.event_type for event in self.world.items.history(7)]
        self.assertIn(ItemEventType.GRABBED, event_types)

    def test_drop_zone_delivery(self) -> None:
        self.world.interactions.grab_nearest("Left", 0.1, self.world.conveyors.values())
        zone = DropZone("truck-zone", "TRUCK", 500.0, 500.0, 700.0, 700.0)
        result = self.world.interactions.release(
            "Left",
            Vec2(600.0, 600.0),
            0.3,
            [zone],
            self.world.conveyors,
            expected_destination="TRUCK",
        )
        self.assertEqual(result, ("correct", 7))
        self.assertEqual(self.world.items.snapshot(7).state, ItemState.DELIVERED)


if __name__ == "__main__":
    unittest.main()
