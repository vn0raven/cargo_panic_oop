from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
TARGET_FPS = 60

BELT_RECT = (0, 286, SCREEN_WIDTH, 200)
BELT_Y = 386
PACKAGE_SIZE = (118, 88)
MAX_ACTIVE_PACKAGES = 4

DESTINATIONS = ("TRUCK", "SHIP", "PLANE", "INSPECTION")

ATTRIBUTE_VALUES = {
    "COLOR": ("RED", "BLUE", "GREEN", "GOLD"),
    "WEIGHT": ("LIGHT", "MEDIUM", "HEAVY", "OVERSIZE"),
    "MARK": ("CIRCLE", "TRIANGLE", "SQUARE", "DIAMOND"),
    "STATUS": ("NORMAL", "FRAGILE", "EXPRESS", "DAMAGED"),
}

WEIGHT_LABELS = {
    "LIGHT": "2 KG",
    "MEDIUM": "8 KG",
    "HEAVY": "18 KG",
    "OVERSIZE": "32 KG",
}

DESTINATION_COLORS = {
    "TRUCK": (238, 161, 67),
    "SHIP": (68, 169, 232),
    "PLANE": (92, 205, 145),
    "INSPECTION": (190, 119, 224),
}

PACKAGE_COLORS = {
    "RED": (218, 74, 78),
    "BLUE": (70, 133, 229),
    "GREEN": (72, 176, 111),
    "GOLD": (225, 179, 56),
}

STATUS_COLORS = {
    "NORMAL": (126, 138, 158),
    "FRAGILE": (236, 86, 86),
    "EXPRESS": (244, 164, 61),
    "DAMAGED": (184, 105, 208),
}

# Default palette. High-contrast mode derives from this in rendering.Theme.
BACKGROUND = (11, 15, 24)
BACKGROUND_2 = (18, 24, 36)
PANEL = (25, 32, 47)
PANEL_2 = (31, 40, 58)
PANEL_BORDER = (63, 79, 108)
INK = (244, 247, 252)
MUTED = (164, 176, 198)
DIM = (103, 116, 142)
ACCENT = (246, 181, 75)
SUCCESS = (105, 224, 155)
DANGER = (246, 94, 94)
WARNING = (250, 190, 72)
FOCUS = (116, 200, 255)


@dataclass(frozen=True, slots=True)
class ContractSpec:
    title: str
    rule_type: str
    package_count: int
    required_correct: int
    belt_speed: float
    spawn_interval: float
    description: str


CONTRACTS = (
    ContractSpec(
        title="COLOR INTAKE",
        rule_type="COLOR",
        package_count=8,
        required_correct=7,
        belt_speed=72.0,
        spawn_interval=2.30,
        description="Read the routing tape. Deliver each parcel by color.",
    ),
    ContractSpec(
        title="WEIGHT CONTROL",
        rule_type="WEIGHT",
        package_count=10,
        required_correct=8,
        belt_speed=82.0,
        spawn_interval=2.05,
        description="Ignore the tape. The printed weight class controls the route.",
    ),
    ContractSpec(
        title="SYMBOL AUDIT",
        rule_type="MARK",
        package_count=12,
        required_correct=10,
        belt_speed=94.0,
        spawn_interval=1.86,
        description="Use the handling mark printed on each parcel.",
    ),
    ContractSpec(
        title="STATUS DESK",
        rule_type="STATUS",
        package_count=14,
        required_correct=12,
        belt_speed=106.0,
        spawn_interval=1.68,
        description="Route standard, fragile, express, and damaged parcels.",
    ),
)

TUTORIAL_CONTRACT = ContractSpec(
    title="TRAINING SHIFT",
    rule_type="COLOR",
    package_count=3,
    required_correct=1,
    belt_speed=44.0,
    spawn_interval=2.8,
    description="Practice grabbing a parcel and releasing it over the matching bay.",
)
