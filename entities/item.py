from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field

from core.enums import ItemState
from core.vector import Vec2
from entities.base_entity import Entity


@dataclass(frozen=True, slots=True)
class ItemAttributes:
    color: str
    weight: str
    mark: str
    status: str
    parcel_type: str = "BOX"


@dataclass(slots=True)
class Item(Entity, ABC):
    attributes: ItemAttributes = field(
        default_factory=lambda: ItemAttributes("RED", "LIGHT", "CIRCLE", "NORMAL")
    )
    state: ItemState = ItemState.QUEUED
    velocity: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    holder_id: str | None = None
    conveyor_id: str | None = None
    source_conveyor_id: str | None = None
    revision: int = 0
    updated_at: float = 0.0
    suspended_at: float | None = None
    reattach_started_at: float | None = None
    reattach_origin: Vec2 | None = None

    @property
    def pickup_radius(self) -> float:
        return 100.0

    @property
    def is_terminal(self) -> bool:
        return self.state in {ItemState.DELIVERED, ItemState.MISSED, ItemState.DISABLED}

    @property
    def can_be_grabbed(self) -> bool:
        return self.active and self.state in {
            ItemState.ON_CONVEYOR,
            ItemState.REATTACHING,
            ItemState.DROPPED,
        }

    def attribute(self, rule_type: str) -> str:
        lookup = {
            "COLOR": self.attributes.color,
            "WEIGHT": self.attributes.weight,
            "MARK": self.attributes.mark,
            "STATUS": self.attributes.status,
        }
        return lookup[rule_type]

    def update(self, dt: float, now: float) -> None:
        # Item movement is applied by its current owner: conveyor or interaction manager.
        del dt, now

    def _touch(self, now: float) -> None:
        self.updated_at = now
        self.revision += 1

    def _set_position(self, position: Vec2, velocity: Vec2, now: float) -> None:
        self.position = position.copy()
        self.velocity = velocity.copy()
        self._touch(now)

    def _attach(self, conveyor_id: str, now: float) -> None:
        self.state = ItemState.ON_CONVEYOR
        self.conveyor_id = conveyor_id
        self.source_conveyor_id = conveyor_id
        self.holder_id = None
        self.suspended_at = None
        self.reattach_started_at = None
        self.reattach_origin = None
        self._touch(now)

    def _start_reattach(self, conveyor_id: str, now: float) -> None:
        self.state = ItemState.REATTACHING
        self.conveyor_id = conveyor_id
        self.source_conveyor_id = conveyor_id
        self.holder_id = None
        self.suspended_at = None
        self.reattach_started_at = now
        self.reattach_origin = self.position.copy()
        self._touch(now)

    def _grab(self, holder_id: str, now: float) -> None:
        self.state = ItemState.HELD
        self.holder_id = holder_id
        # Keep source_conveyor_id as memory, but remove current conveyor ownership.
        self.conveyor_id = None
        self.suspended_at = None
        self.reattach_started_at = None
        self.reattach_origin = None
        self.velocity = Vec2(0.0, 0.0)
        self._touch(now)

    def _suspend_tracking(self, now: float) -> None:
        self.state = ItemState.TRACKING_SUSPENDED
        self.suspended_at = now
        self.velocity = Vec2(0.0, 0.0)
        self._touch(now)

    def _resume_tracking(self, holder_id: str, now: float) -> None:
        self.state = ItemState.HELD
        self.holder_id = holder_id
        self.suspended_at = None
        self._touch(now)

    def _release(self, position: Vec2, now: float) -> None:
        self._set_position(position, Vec2(0.0, 0.0), now)
        self.state = ItemState.DROPPED
        self.holder_id = None
        self.conveyor_id = None
        self.suspended_at = None
        self._touch(now)

    def _deliver(self, position: Vec2, now: float) -> None:
        self._set_position(position, Vec2(0.0, 0.0), now)
        self.state = ItemState.DELIVERED
        self.holder_id = None
        self.conveyor_id = None
        self.active = False
        self._touch(now)

    def _miss(self, now: float) -> None:
        self.state = ItemState.MISSED
        self.holder_id = None
        self.conveyor_id = None
        self.active = False
        self._touch(now)


@dataclass(slots=True)
class PackageItem(Item):
    """Default parcel. New parcel types extend this class without changing managers."""


@dataclass(slots=True)
class HeavyPackageItem(PackageItem):
    @property
    def pickup_radius(self) -> float:
        return 82.0
