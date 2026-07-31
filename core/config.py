from __future__ import annotations

from dataclasses import dataclass

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Cargo Panic: Night Shift"

BACKGROUND = (12, 17, 25)
PANEL = (24, 31, 43)
PANEL_2 = (34, 43, 58)
PANEL_BORDER = (68, 84, 108)
INK = (239, 243, 249)
MUTED = (166, 178, 198)
ACCENT = (244, 178, 73)
SUCCESS = (91, 214, 147)
DANGER = (244, 89, 89)
WARNING = (246, 205, 76)
BELT_DARK = (38, 44, 54)
BELT_LIGHT = (67, 76, 91)

DESTINATION_COLORS = {
    "Northport": (81, 172, 231),
    "Eastvale": (111, 205, 139),
    "Westhaven": (218, 137, 216),
}

PACKAGE_BODY_COLORS = {
    "Standard": (178, 134, 85),
    "Small": (213, 202, 176),
    "Heavy": (118, 78, 47),
}

TAG_COLORS = {
    "Standard": (109, 122, 143),
    "Fragile": (229, 92, 91),
    "Refrigerated": (72, 184, 224),
    "Express": (239, 166, 62),
    "Damaged": (185, 104, 210),
}

BELT_RECT = (0, 260, SCREEN_WIDTH, 190)
CONTAINER_TOP = 510
CONTAINER_HEIGHT = 170
PACKAGE_SIZE = (112, 78)


@dataclass(frozen=True, slots=True)
class PhaseSpec:
    name: str
    subtitle: str
    duration: float
    belt_speed: float
    spawn_interval: float
    max_active: int
    allowed_kinds: tuple[str, ...]
    allowed_tags: tuple[str, ...]
    closure_enabled: bool = False
    surge_enabled: bool = False


PHASES = (
    PhaseSpec(
        name="Training Shift",
        subtitle="Match each destination label to its shipping bay.",
        duration=45.0,
        belt_speed=78.0,
        spawn_interval=2.8,
        max_active=3,
        allowed_kinds=("Standard", "Small"),
        allowed_tags=("Standard",),
    ),
    PhaseSpec(
        name="Normal Operations",
        subtitle="Build a clean rhythm. Accuracy protects your combo.",
        duration=55.0,
        belt_speed=92.0,
        spawn_interval=2.15,
        max_active=5,
        allowed_kinds=("Standard", "Small", "Heavy"),
        allowed_tags=("Standard", "Express"),
    ),
    PhaseSpec(
        name="Handling Requirements",
        subtitle="Prioritize express and refrigerated cargo. Handle fragile boxes carefully.",
        duration=60.0,
        belt_speed=104.0,
        spawn_interval=1.8,
        max_active=6,
        allowed_kinds=("Standard", "Small", "Heavy"),
        allowed_tags=("Standard", "Fragile", "Refrigerated", "Express", "Damaged"),
    ),
    PhaseSpec(
        name="System Malfunction",
        subtitle="Shipping bays may close. Watch the warning lights.",
        duration=60.0,
        belt_speed=112.0,
        spawn_interval=1.55,
        max_active=7,
        allowed_kinds=("Standard", "Small", "Heavy"),
        allowed_tags=("Standard", "Fragile", "Refrigerated", "Express", "Damaged"),
        closure_enabled=True,
        surge_enabled=True,
    ),
    PhaseSpec(
        name="Final Rush",
        subtitle="Keep the line alive until the night shift ends.",
        duration=60.0,
        belt_speed=126.0,
        spawn_interval=1.25,
        max_active=8,
        allowed_kinds=("Standard", "Small", "Heavy"),
        allowed_tags=("Standard", "Fragile", "Refrigerated", "Express", "Damaged"),
        closure_enabled=True,
        surge_enabled=True,
    ),
)
