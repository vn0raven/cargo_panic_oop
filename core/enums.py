from __future__ import annotations

from enum import Enum, auto


class ItemState(Enum):
    QUEUED = auto()
    ON_CONVEYOR = auto()
    HELD = auto()
    TRACKING_SUSPENDED = auto()
    REATTACHING = auto()
    DROPPED = auto()
    DELIVERED = auto()
    MISSED = auto()
    DISABLED = auto()


class ItemEventType(Enum):
    REGISTERED = auto()
    POSITION_CHANGED = auto()
    ATTACHED_TO_CONVEYOR = auto()
    GRABBED = auto()
    RELEASED = auto()
    TRACKING_LOST = auto()
    TRACKING_RECOVERED = auto()
    REATTACH_STARTED = auto()
    REATTACHED = auto()
    DELIVERED = auto()
    MISSED = auto()
