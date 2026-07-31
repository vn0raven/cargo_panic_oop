from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.enums import ItemState
from core.vector import Vec2
from managers.item_tracking_manager import ItemTrackingManager


@dataclass(slots=True)
class Conveyor(ABC):
    conveyor_id: str
    center_y: float
    speed: float
    left_bound: float
    right_bound: float
    attached_item_ids: set[int] = field(default_factory=set)

    def add_item(self, item_id: int) -> None:
        self.attached_item_ids.add(item_id)

    def remove_item(self, item_id: int) -> None:
        self.attached_item_ids.discard(item_id)

    @abstractmethod
    def update(self, tracker: ItemTrackingManager, dt: float, now: float) -> list[int]:
        raise NotImplementedError


@dataclass(slots=True)
class LinearConveyor(Conveyor):
    reattach_duration: float = 0.22

    def attach(
        self,
        tracker: ItemTrackingManager,
        item_id: int,
        now: float,
        *,
        smooth: bool,
    ) -> None:
        item = tracker.get(item_id)
        self.add_item(item_id)
        if smooth and abs(item.position.y - self.center_y) > 0.5:
            # The release position is preserved and becomes the interpolation origin.
            # No code writes the item directly back to the belt center.
            tracker.start_reattach(item_id, self.conveyor_id, now)
        else:
            tracker.move(item_id, Vec2(item.position.x, self.center_y), Vec2(self.speed, 0.0), now)
            tracker.attach(item_id, self.conveyor_id, now)

    def detach(self, item_id: int) -> None:
        self.remove_item(item_id)

    def contains_x(self, x: float) -> bool:
        return self.left_bound <= x <= self.right_bound

    def update(self, tracker: ItemTrackingManager, dt: float, now: float) -> list[int]:
        missed: list[int] = []
        for item_id in tuple(self.attached_item_ids):
            item = tracker.get(item_id)
            if not item.active:
                self.remove_item(item_id)
                continue

            if item.state is ItemState.ON_CONVEYOR:
                next_position = Vec2(item.position.x + self.speed * dt, self.center_y)
                tracker.move(item_id, next_position, Vec2(self.speed, 0.0), now)
            elif item.state is ItemState.REATTACHING:
                origin = item.reattach_origin or item.position
                started_at = item.reattach_started_at if item.reattach_started_at is not None else now
                progress = min(1.0, max(0.0, (now - started_at) / max(self.reattach_duration, 1e-6)))
                target = Vec2(item.position.x + self.speed * dt, self.center_y)
                next_position = Vec2(target.x, origin.y + (self.center_y - origin.y) * progress)
                tracker.move(item_id, next_position, Vec2(self.speed, 0.0), now)
                if progress >= 1.0:
                    tracker.complete_reattach(item_id, self.conveyor_id, now)
            else:
                # Held, suspended, or dropped items are not conveyor-owned.
                self.remove_item(item_id)
                continue

            if tracker.get(item_id).position.x > self.right_bound:
                tracker.miss(item_id, now)
                self.remove_item(item_id)
                missed.append(item_id)
        return missed
