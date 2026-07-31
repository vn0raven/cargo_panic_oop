from __future__ import annotations

from dataclasses import dataclass, field

from core.vector import Vec2


@dataclass(slots=True)
class PlayerInteractor:
    player_id: str
    pointer_position: Vec2
    tracked: bool = True
    held_item_id: int | None = None
    tracking_lost_at: float | None = None

    def move_pointer(self, position: Vec2) -> None:
        self.pointer_position = position.copy()

    def begin_hold(self, item_id: int) -> None:
        if self.held_item_id is not None and self.held_item_id != item_id:
            raise RuntimeError(f"{self.player_id} is already holding item {self.held_item_id}")
        self.held_item_id = item_id

    def end_hold(self) -> None:
        self.held_item_id = None

    def mark_tracking_lost(self, now: float) -> None:
        self.tracked = False
        self.tracking_lost_at = now

    def mark_tracking_recovered(self) -> None:
        self.tracked = True
        self.tracking_lost_at = None
