from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from core.enums import ItemEventType, ItemState
from core.events import ItemEvent, ItemSnapshot
from core.vector import Vec2
from entities.item import Item


class ItemTrackingManager:
    """Single source of truth for item identity, state, transform, and history."""

    def __init__(self) -> None:
        self._items: dict[int, Item] = {}
        self._snapshots: dict[int, ItemSnapshot] = {}
        self._history: dict[int, list[ItemEvent]] = defaultdict(list)
        self._sequence = 0

    def register(self, item: Item, now: float) -> None:
        if item.entity_id in self._items:
            raise ValueError(f"Duplicate item id: {item.entity_id}")
        item.updated_at = now
        self._items[item.entity_id] = item
        self._record(item, ItemEventType.REGISTERED)

    def get(self, item_id: int) -> Item:
        try:
            return self._items[item_id]
        except KeyError as error:
            raise KeyError(f"Unknown item id: {item_id}") from error

    def items(self) -> tuple[Item, ...]:
        return tuple(self._items.values())

    def active_items(self) -> tuple[Item, ...]:
        return tuple(item for item in self._items.values() if item.active)

    def snapshot(self, item_id: int) -> ItemSnapshot:
        return self._snapshots[item_id]

    def history(self, item_id: int) -> tuple[ItemEvent, ...]:
        return tuple(self._history[item_id])

    def nearest_grabbable(self, position: Vec2, maximum_distance: float = 100.0) -> Item | None:
        candidates = [
            item
            for item in self._items.values()
            if item.can_be_grabbed
            and item.position.distance_to(position) <= min(maximum_distance, item.pickup_radius)
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: item.position.distance_squared_to(position))

    def attach(self, item_id: int, conveyor_id: str, now: float) -> None:
        item = self.get(item_id)
        item._attach(conveyor_id, now)
        self._record(item, ItemEventType.ATTACHED_TO_CONVEYOR)

    def start_reattach(self, item_id: int, conveyor_id: str, now: float) -> None:
        item = self.get(item_id)
        item._start_reattach(conveyor_id, now)
        self._record(item, ItemEventType.REATTACH_STARTED)

    def complete_reattach(self, item_id: int, conveyor_id: str, now: float) -> None:
        item = self.get(item_id)
        item._attach(conveyor_id, now)
        self._record(item, ItemEventType.REATTACHED)

    def grab(self, item_id: int, holder_id: str, now: float) -> None:
        item = self.get(item_id)
        if not item.can_be_grabbed:
            raise RuntimeError(f"Item {item_id} cannot be grabbed from state {item.state.name}")
        item._grab(holder_id, now)
        self._record(item, ItemEventType.GRABBED, actor_id=holder_id)

    def move(self, item_id: int, position: Vec2, velocity: Vec2, now: float) -> None:
        item = self.get(item_id)
        item._set_position(position, velocity, now)
        self._record(item, ItemEventType.POSITION_CHANGED, actor_id=item.holder_id)

    def suspend_tracking(self, item_id: int, holder_id: str, now: float) -> None:
        item = self.get(item_id)
        if item.holder_id != holder_id or item.state is not ItemState.HELD:
            return
        item._suspend_tracking(now)
        self._record(item, ItemEventType.TRACKING_LOST, actor_id=holder_id)

    def resume_tracking(self, item_id: int, holder_id: str, now: float) -> None:
        item = self.get(item_id)
        if item.state is not ItemState.TRACKING_SUSPENDED:
            return
        item._resume_tracking(holder_id, now)
        self._record(item, ItemEventType.TRACKING_RECOVERED, actor_id=holder_id)

    def release(self, item_id: int, position: Vec2, holder_id: str, now: float) -> None:
        item = self.get(item_id)
        item._release(position, now)
        self._record(item, ItemEventType.RELEASED, actor_id=holder_id)

    def deliver(self, item_id: int, position: Vec2, holder_id: str, now: float, note: str = "") -> None:
        item = self.get(item_id)
        item._deliver(position, now)
        self._record(item, ItemEventType.DELIVERED, actor_id=holder_id, note=note)

    def miss(self, item_id: int, now: float) -> None:
        item = self.get(item_id)
        item._miss(now)
        self._record(item, ItemEventType.MISSED)

    def _snapshot_for(self, item: Item) -> ItemSnapshot:
        return ItemSnapshot(
            item_id=item.entity_id,
            state=item.state,
            x=item.position.x,
            y=item.position.y,
            velocity_x=item.velocity.x,
            velocity_y=item.velocity.y,
            holder_id=item.holder_id,
            conveyor_id=item.conveyor_id,
            revision=item.revision,
            updated_at=item.updated_at,
        )

    def _record(
        self,
        item: Item,
        event_type: ItemEventType,
        actor_id: str | None = None,
        note: str = "",
    ) -> None:
        snapshot = self._snapshot_for(item)
        self._snapshots[item.entity_id] = snapshot
        self._sequence += 1
        self._history[item.entity_id].append(
            ItemEvent(
                sequence=self._sequence,
                item_id=item.entity_id,
                event_type=event_type,
                snapshot=snapshot,
                actor_id=actor_id,
                note=note,
            )
        )
