from __future__ import annotations

from enum import Enum, auto


class GameState(Enum):
    TITLE = auto()
    PLAYING = auto()
    PAUSED = auto()
    RESULTS = auto()


class Destination(Enum):
    NORTHPORT = "Northport"
    EASTVALE = "Eastvale"
    WESTHAVEN = "Westhaven"


class PackageKind(Enum):
    STANDARD = "Standard"
    SMALL = "Small"
    HEAVY = "Heavy"


class HandlingTag(Enum):
    NONE = "Standard"
    FRAGILE = "Fragile"
    REFRIGERATED = "Refrigerated"
    EXPRESS = "Express"
    DAMAGED = "Damaged"


class PackageState(Enum):
    ON_BELT = auto()
    HELD = auto()
    SCANNING = auto()
    DELIVERED = auto()
    MISSED = auto()
