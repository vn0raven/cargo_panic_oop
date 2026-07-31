from __future__ import annotations

from dataclasses import dataclass

from core.enums import ItemEventType, ItemState


@dataclass(frozen=True, slots=True)
class ItemSnapshot:
    item_id: int
    state: ItemState
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    holder_id: str | None
    conveyor_id: str | None
    revision: int
    updated_at: float


@dataclass(frozen=True, slots=True)
class ItemEvent:
    sequence: int
    item_id: int
    event_type: ItemEventType
    snapshot: ItemSnapshot
    actor_id: str | None = None
    note: str = ""
