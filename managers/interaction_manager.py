from __future__ import annotations

from collections.abc import Iterable

from core.enums import ItemState
from core.vector import Vec2
from entities.player import PlayerInteractor
from interactables.conveyor import LinearConveyor
from interactables.drop_zone import DropZone
from managers.item_tracking_manager import ItemTrackingManager


class PlayerInteractionManager:
    """Owns player-to-item transfers. It never edits item fields directly."""

    def __init__(
        self,
        tracker: ItemTrackingManager,
        *,
        tracking_grace_seconds: float = 1.25,
    ) -> None:
        self._tracker = tracker
        self._players: dict[str, PlayerInteractor] = {}
        self._tracking_grace_seconds = tracking_grace_seconds

    def register_player(self, player: PlayerInteractor) -> None:
        if player.player_id in self._players:
            raise ValueError(f"Duplicate player id: {player.player_id}")
        self._players[player.player_id] = player

    def get_player(self, player_id: str) -> PlayerInteractor:
        return self._players[player_id]

    def update_pointer(self, player_id: str, position: Vec2, now: float) -> None:
        player = self.get_player(player_id)
        player.move_pointer(position)
        if player.held_item_id is None or not player.tracked:
            return
        item = self._tracker.get(player.held_item_id)
        if item.state is ItemState.HELD:
            self._tracker.move(item.entity_id, position, Vec2(0.0, 0.0), now)

    def grab_nearest(
        self,
        player_id: str,
        now: float,
        conveyors: Iterable[LinearConveyor],
        maximum_distance: float = 100.0,
    ) -> int | None:
        player = self.get_player(player_id)
        if player.held_item_id is not None:
            return player.held_item_id

        item = self._tracker.nearest_grabbable(player.pointer_position, maximum_distance)
        if item is None:
            return None

        # Detach first so the conveyor cannot advance the same item this frame.
        for conveyor in conveyors:
            conveyor.detach(item.entity_id)

        self._tracker.grab(item.entity_id, player_id, now)
        player.begin_hold(item.entity_id)
        return item.entity_id

    def release(
        self,
        player_id: str,
        position: Vec2,
        now: float,
        drop_zones: Iterable[DropZone],
        conveyors: dict[str, LinearConveyor],
        expected_destination: str | None = None,
    ) -> tuple[str, int] | None:
        player = self.get_player(player_id)
        item_id = player.held_item_id
        if item_id is None:
            return None

        item = self._tracker.get(item_id)
        zone = next((candidate for candidate in drop_zones if candidate.contains(position)), None)

        if zone is not None:
            self._tracker.deliver(
                item_id,
                zone.center,
                player_id,
                now,
                note=f"destination={zone.destination}",
            )
            outcome = "correct" if expected_destination is None or zone.destination == expected_destination else "wrong"
            player.end_hold()
            return outcome, item_id

        # Record the exact release point before any conveyor policy is applied.
        self._tracker.release(item_id, position, player_id, now)
        player.end_hold()

        source_id = item.source_conveyor_id
        source = conveyors.get(source_id) if source_id is not None else None
        if source is not None:
            # Original gameplay returns invalid drops to the source belt, but now it
            # reattaches through a timed state instead of snapping y to BELT_Y.
            source.attach(self._tracker, item_id, now, smooth=True)
            return "reattaching", item_id

        return "dropped", item_id

    def tracking_lost(self, player_id: str, now: float) -> None:
        player = self.get_player(player_id)
        if not player.tracked:
            return
        player.mark_tracking_lost(now)
        if player.held_item_id is not None:
            # The item stays at its last exact position and remembers its holder.
            self._tracker.suspend_tracking(player.held_item_id, player_id, now)

    def tracking_recovered(self, player_id: str, position: Vec2, now: float) -> None:
        player = self.get_player(player_id)
        player.mark_tracking_recovered()
        player.move_pointer(position)
        if player.held_item_id is not None:
            self._tracker.resume_tracking(player.held_item_id, player_id, now)
            self._tracker.move(player.held_item_id, position, Vec2(0.0, 0.0), now)

    def update(self, now: float) -> list[int]:
        """Resolve only prolonged tracking loss; never reset an item to a belt."""
        released_in_place: list[int] = []
        for player in self._players.values():
            if player.tracked or player.held_item_id is None or player.tracking_lost_at is None:
                continue
            if now - player.tracking_lost_at < self._tracking_grace_seconds:
                continue

            item_id = player.held_item_id
            item = self._tracker.get(item_id)
            # Preserve the last snapshot location. A timeout becomes a world drop,
            # not an implicit conveyor reset.
            self._tracker.release(item_id, item.position, player.player_id, now)
            player.end_hold()
            released_in_place.append(item_id)
        return released_in_place
