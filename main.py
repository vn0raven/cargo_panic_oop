from __future__ import annotations

import argparse
import gc
import math
import multiprocessing as mp
import queue
import random
import time
from collections import Counter, deque
from dataclasses import dataclass, field

import pygame
from pygame.math import Vector2

from application.game_world import GameWorld
from core.enums import ItemState
from core.vector import Vec2
from entities.item import ItemAttributes, PackageItem
from entities.player import PlayerInteractor
from interactables.conveyor import LinearConveyor
from interactables.drop_zone import DropZone



SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_SIZE = (SCREEN_WIDTH, SCREEN_HEIGHT)
TARGET_FPS = 60

TRACKING_TIMEOUT = 0.65
HAND_STATE_HISTORY = 5
HAND_STATE_VOTES = 3

BELT_Y = 347
BELT_HEIGHT = 154
PACKAGE_WIDTH = 112
PACKAGE_HEIGHT = 82
MAX_ACTIVE_PACKAGES = 4

DESTINATIONS = (
    "TRUCK",
    "SHIP",
    "PLANE",
    "INSPECTION",
)

DESTINATION_COLORS = {
    "TRUCK": (232, 157, 70),
    "SHIP": (79, 170, 222),
    "PLANE": (117, 203, 139),
    "INSPECTION": (190, 123, 213),
}

ATTRIBUTE_VALUES = {
    "COLOR": ("RED", "BLUE", "GREEN", "GOLD"),
    "WEIGHT": ("LIGHT", "MEDIUM", "HEAVY", "OVERSIZE"),
    "MARK": ("CIRCLE", "TRIANGLE", "SQUARE", "DIAMOND"),
    "STATUS": ("NORMAL", "FRAGILE", "EXPRESS", "DAMAGED"),
}

PACKAGE_COLORS = {
    "RED": (217, 79, 77),
    "BLUE": (72, 139, 224),
    "GREEN": (81, 179, 111),
    "GOLD": (226, 182, 66),
}

STATUS_COLORS = {
    "NORMAL": (111, 123, 139),
    "FRAGILE": (221, 79, 77),
    "EXPRESS": (238, 157, 58),
    "DAMAGED": (177, 99, 193),
}

WEIGHT_TEXT = {
    "LIGHT": "2 KG",
    "MEDIUM": "8 KG",
    "HEAVY": "18 KG",
    "OVERSIZE": "32 KG",
}

PARCEL_BODY_COLORS = {
    "BOX": (185, 140, 87),
    "MAILER": (217, 207, 181),
    "CRATE": (126, 85, 50),
}

HAND_COLORS = {
    "Left": (255, 186, 76),
    "Right": (84, 216, 255),
    "Mouse": (232, 235, 241),
}

INK = (238, 241, 247)
MUTED = (174, 184, 204)
PANEL = (26, 32, 44)
PANEL_BORDER = (66, 79, 105)
BACKGROUND = (13, 18, 27)
ACCENT = (244, 176, 74)
SUCCESS = (116, 220, 159)
DANGER = (244, 94, 94)


@dataclass(frozen=True, slots=True)
class LevelSpec:
    title: str
    rule_type: str
    package_count: int
    required_correct: int
    belt_speed: float
    spawn_interval: float
    description: str


LEVELS = (
    LevelSpec(
        title="COLOR INTAKE",
        rule_type="COLOR",
        package_count=8,
        required_correct=7,
        belt_speed=72.0,
        spawn_interval=2.35,
        description="Read the routing tape. Deliver each parcel by color.",
    ),
    LevelSpec(
        title="WEIGHT CONTROL",
        rule_type="WEIGHT",
        package_count=10,
        required_correct=8,
        belt_speed=82.0,
        spawn_interval=2.12,
        description="Ignore the tape. The printed weight class controls the route.",
    ),
    LevelSpec(
        title="SYMBOL AUDIT",
        rule_type="MARK",
        package_count=12,
        required_correct=10,
        belt_speed=92.0,
        spawn_interval=1.92,
        description="Use the white handling mark printed on each parcel.",
    ),
    LevelSpec(
        title="STATUS DESK",
        rule_type="STATUS",
        package_count=14,
        required_correct=12,
        belt_speed=104.0,
        spawn_interval=1.72,
        description="Route parcels by standard, fragile, express, or damaged status.",
    ),
)


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    font = pygame.font.SysFont("segoeui,arial", size, bold=bold)
    if font is None:
        return pygame.font.Font(None, size)
    return font


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill: tuple[int, int, int] = PANEL,
    border: tuple[int, int, int] = PANEL_BORDER,
    radius: int = 14,
    border_width: int = 2,
) -> None:
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(
        surface,
        border,
        rect,
        border_width,
        border_radius=radius,
    )


def blit_centered(
    surface: pygame.Surface,
    rendered: pygame.Surface,
    center: tuple[int, int] | Vector2,
) -> pygame.Rect:
    rect = rendered.get_rect(center=center)
    surface.blit(rendered, rect)
    return rect


def draw_barcode(
    surface: pygame.Surface,
    rect: pygame.Rect,
    seed: int,
) -> None:
    rng = random.Random(seed)
    pygame.draw.rect(surface, (248, 248, 243), rect, border_radius=2)
    x = rect.x + 2

    while x < rect.right - 2:
        width = rng.choice((1, 1, 2, 2, 3))
        gap = rng.choice((1, 2))
        pygame.draw.rect(
            surface,
            (27, 29, 33),
            pygame.Rect(
                x,
                rect.y + 2,
                min(width, rect.right - x - 1),
                max(1, rect.height - 4),
            ),
        )
        x += width + gap


def draw_mark_icon(
    surface: pygame.Surface,
    mark: str,
    center: Vector2 | tuple[float, float],
    color: tuple[int, int, int],
    size: int = 10,
    width: int = 2,
) -> None:
    center = Vector2(center)
    x = round(center.x)
    y = round(center.y)

    if mark == "CIRCLE":
        pygame.draw.circle(surface, color, (x, y), size, width)
    elif mark == "TRIANGLE":
        pygame.draw.polygon(
            surface,
            color,
            ((x, y - size), (x - size, y + size - 2), (x + size, y + size - 2)),
            width,
        )
    elif mark == "SQUARE":
        pygame.draw.rect(
            surface,
            color,
            pygame.Rect(x - size, y - size, size * 2, size * 2),
            width,
        )
    else:
        pygame.draw.polygon(
            surface,
            color,
            ((x, y - size), (x + size, y), (x, y + size), (x - size, y)),
            width,
        )


def draw_destination_icon(
    surface: pygame.Surface,
    name: str,
    center: tuple[int, int],
    color: tuple[int, int, int],
    scale: float = 1.0,
) -> None:
    x, y = center
    s = scale
    dark = (26, 30, 39)

    def rect(rx: float, ry: float, rw: float, rh: float) -> pygame.Rect:
        return pygame.Rect(
            round(x + rx * s),
            round(y + ry * s),
            round(rw * s),
            round(rh * s),
        )

    if name == "TRUCK":
        pygame.draw.rect(surface, color, rect(-49, -17, 59, 31), border_radius=5)
        pygame.draw.polygon(
            surface,
            color,
            (
                (round(x + 10 * s), round(y - 11 * s)),
                (round(x + 31 * s), round(y - 11 * s)),
                (round(x + 45 * s), round(y + 3 * s)),
                (round(x + 45 * s), round(y + 14 * s)),
                (round(x + 10 * s), round(y + 14 * s)),
            ),
        )
        pygame.draw.rect(surface, INK, rect(22, -7, 13, 9), border_radius=2)
        for wheel_x in (-29, 29):
            pygame.draw.circle(
                surface,
                dark,
                (round(x + wheel_x * s), round(y + 18 * s)),
                max(3, round(8 * s)),
            )
            pygame.draw.circle(
                surface,
                INK,
                (round(x + wheel_x * s), round(y + 18 * s)),
                max(1, round(3 * s)),
            )
    elif name == "SHIP":
        pygame.draw.polygon(
            surface,
            color,
            (
                (round(x - 51 * s), round(y + 2 * s)),
                (round(x + 49 * s), round(y + 2 * s)),
                (round(x + 31 * s), round(y + 22 * s)),
                (round(x - 35 * s), round(y + 22 * s)),
            ),
        )
        pygame.draw.rect(surface, INK, rect(-18, -18, 41, 20), border_radius=3)
        pygame.draw.rect(surface, color, rect(-6, -31, 12, 13))
        for wave_x in (-37, -4, 28):
            pygame.draw.arc(
                surface,
                INK,
                rect(wave_x, 20, 26, 12),
                0.15,
                math.pi - 0.15,
                max(1, round(2 * s)),
            )
    elif name == "PLANE":
        pygame.draw.polygon(
            surface,
            color,
            tuple(
                (round(x + px * s), round(y + py * s))
                for px, py in (
                    (-52, 7), (-8, -2), (22, -27), (34, -25), (18, -1),
                    (52, 8), (45, 17), (12, 9), (-8, 29), (-17, 27),
                    (-8, 8), (-48, 16),
                )
            ),
        )
        pygame.draw.circle(surface, INK, (round(x + 8 * s), round(y + 2 * s)), max(2, round(4 * s)))
    else:
        pygame.draw.rect(surface, color, rect(-42, -26, 84, 52), 5, border_radius=8)
        pygame.draw.rect(surface, INK, rect(-20, -12, 40, 28), border_radius=4)
        pygame.draw.line(
            surface,
            dark,
            (round(x - 12 * s), round(y - 3 * s)),
            (round(x + 12 * s), round(y + 7 * s)),
            max(2, round(4 * s)),
        )
        pygame.draw.line(
            surface,
            INK,
            (round(x - 27 * s), round(y + 26 * s)),
            (round(x - 27 * s), round(y + 35 * s)),
            max(2, round(4 * s)),
        )
        pygame.draw.line(
            surface,
            INK,
            (round(x + 27 * s), round(y + 26 * s)),
            (round(x + 27 * s), round(y + 35 * s)),
            max(2, round(4 * s)),
        )


@dataclass(slots=True)
class ContainerZone:
    name: str
    rect: pygame.Rect

    def draw(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        small_font: pygame.font.Font,
        highlighted: bool,
    ) -> None:
        color = DESTINATION_COLORS[self.name]
        bay = self.rect
        shadow = bay.move(0, 5)

        pygame.draw.rect(surface, (8, 11, 17), shadow, border_radius=14)
        pygame.draw.rect(surface, (21, 27, 37), bay, border_radius=14)

        title_bar = pygame.Rect(bay.x + 7, bay.y + 7, bay.width - 14, 29)
        pygame.draw.rect(surface, color, title_bar, border_radius=7)
        blit_centered(surface, font.render(self.name, True, INK), title_bar.center)

        shutter = pygame.Rect(bay.x + 11, bay.y + 40, bay.width - 22, bay.height - 51)
        pygame.draw.rect(surface, (39, 46, 59), shutter, border_radius=8)
        for y in range(shutter.y + 8, shutter.bottom, 12):
            pygame.draw.line(surface, (58, 67, 82), (shutter.x + 5, y), (shutter.right - 5, y), 2)

        draw_destination_icon(surface, self.name, (bay.centerx, bay.centery + 18), color, 0.78)

        border_width = 6 if highlighted else 2
        pygame.draw.rect(surface, color, bay, border_width, border_radius=14)
        if highlighted:
            pygame.draw.rect(surface, INK, bay.inflate(-10, -10), 2, border_radius=10)

        instruction = small_font.render("OPEN HAND TO DROP", True, (218, 224, 236))
        surface.blit(instruction, instruction.get_rect(midbottom=(bay.centerx, bay.bottom - 5)))


@dataclass(slots=True)
class Package:
    package_id: int
    position: Vector2
    parcel_type: str
    color: str
    weight: str
    mark: str
    status: str
    held_by: str | None = None
    alive: bool = True

    def attribute(self, rule_type: str) -> str:
        if rule_type == "COLOR":
            return self.color
        if rule_type == "WEIGHT":
            return self.weight
        if rule_type == "MARK":
            return self.mark
        return self.status

    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            round(self.position.x - PACKAGE_WIDTH / 2),
            round(self.position.y - PACKAGE_HEIGHT / 2),
            PACKAGE_WIDTH,
            PACKAGE_HEIGHT,
        )

    def draw(
        self,
        surface: pygame.Surface,
        small_font: pygame.font.Font,
        tiny_font: pygame.font.Font,
        rule_type: str,
    ) -> None:
        rect = self.rect()
        body_color = PARCEL_BODY_COLORS[self.parcel_type]
        route_color = PACKAGE_COLORS[self.color]
        status_color = STATUS_COLORS[self.status]

        pygame.draw.rect(surface, (10, 13, 19), rect.move(7, 8), border_radius=10)

        if self.parcel_type == "MAILER":
            pygame.draw.rect(surface, body_color, rect, border_radius=14)
            pygame.draw.polygon(
                surface,
                (197, 187, 161),
                ((rect.x + 3, rect.y + 7), (rect.centerx, rect.y + 34), (rect.right - 3, rect.y + 7)),
            )
            pygame.draw.line(surface, route_color, (rect.x + 6, rect.bottom - 12), (rect.right - 6, rect.bottom - 12), 7)
        elif self.parcel_type == "CRATE":
            pygame.draw.rect(surface, body_color, rect, border_radius=5)
            for x in range(rect.x + 8, rect.right, 21):
                pygame.draw.line(surface, (93, 59, 35), (x, rect.y + 4), (x, rect.bottom - 4), 3)
            pygame.draw.line(surface, route_color, (rect.x + 5, rect.centery), (rect.right - 5, rect.centery), 8)
            for corner in (
                (rect.x + 5, rect.y + 5),
                (rect.right - 12, rect.y + 5),
                (rect.x + 5, rect.bottom - 12),
                (rect.right - 12, rect.bottom - 12),
            ):
                pygame.draw.rect(surface, (72, 73, 77), pygame.Rect(corner[0], corner[1], 7, 7))
        else:
            pygame.draw.rect(surface, body_color, rect, border_radius=8)
            pygame.draw.line(surface, (151, 107, 64), (rect.centerx, rect.y + 3), (rect.centerx, rect.bottom - 3), 2)
            pygame.draw.rect(surface, route_color, pygame.Rect(rect.centerx - 8, rect.y + 2, 16, rect.height - 4))

        pygame.draw.rect(surface, (242, 231, 204), rect, 3, border_radius=8)

        label_rect = pygame.Rect(rect.x + 41, rect.y + 8, 64, 51)
        pygame.draw.rect(surface, (249, 249, 243), label_rect, border_radius=3)
        pygame.draw.rect(surface, (32, 34, 38), label_rect, 1, border_radius=3)

        surface.blit(tiny_font.render(f"CP-{self.package_id:04d}", True, (28, 30, 34)), (label_rect.x + 4, label_rect.y + 2))
        surface.blit(tiny_font.render(f"HUB {1 + self.package_id % 9:02d}", True, (28, 30, 34)), (label_rect.x + 4, label_rect.y + 15))
        draw_barcode(
            surface,
            pygame.Rect(label_rect.x + 4, label_rect.bottom - 17, label_rect.width - 8, 13),
            self.package_id * 37,
        )

        status_rect = pygame.Rect(rect.x + 5, rect.y + 7, 32, 18)
        pygame.draw.rect(surface, status_color, status_rect, border_radius=4)
        status_short = {"NORMAL": "STD", "FRAGILE": "FRAG", "EXPRESS": "EXP", "DAMAGED": "DMG"}[self.status]
        blit_centered(surface, tiny_font.render(status_short, True, INK), status_rect.center)

        weight_rect = pygame.Rect(rect.x + 5, rect.y + 31, 32, 18)
        pygame.draw.rect(surface, (235, 226, 199), weight_rect, border_radius=4)
        blit_centered(surface, tiny_font.render(WEIGHT_TEXT[self.weight], True, (32, 34, 38)), weight_rect.center)

        draw_mark_icon(surface, self.mark, (rect.x + 21, rect.bottom - 15), INK, size=8, width=2)
        surface.blit(tiny_font.render(self.parcel_type, True, INK), (rect.x + 36, rect.bottom - 20))

        relevant = self.attribute(rule_type)
        if rule_type == "COLOR":
            relevant_color = route_color
        elif rule_type == "STATUS":
            relevant_color = status_color
        else:
            relevant_color = (246, 216, 92)

        label = small_font.render(f"{rule_type}: {relevant}", True, INK)
        label_rect_out = label.get_rect(midtop=(rect.centerx, rect.bottom + 5))
        background = label_rect_out.inflate(12, 5)
        pygame.draw.rect(surface, (22, 27, 36), background, border_radius=6)
        pygame.draw.rect(surface, relevant_color, background, 2, border_radius=6)
        surface.blit(label, label_rect_out)


@dataclass(slots=True)
class HandController:
    hand_id: str
    handedness: str
    target: Vector2
    position: Vector2
    last_seen: float
    raw_state: str = "neutral"
    stable_state: str = "neutral"
    state_since: float = 0.0
    last_action_at: float = -999.0
    history: deque[str] = field(default_factory=lambda: deque(maxlen=HAND_STATE_HISTORY))
    held_package_id: int | None = None

    def update_state(self, raw_state: str, now: float) -> None:
        self.raw_state = raw_state
        self.history.append(raw_state)
        state, count = Counter(self.history).most_common(1)[0]
        if count >= HAND_STATE_VOTES and state != self.stable_state:
            self.stable_state = state
            self.state_since = now

    def smooth_position(self, dt: float) -> None:
        alpha = 1.0 - math.exp(-22.0 * dt)
        self.position = self.position.lerp(self.target, alpha)


@dataclass(slots=True)
class Particle:
    position: Vector2
    velocity: Vector2
    life: float
    max_life: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> None:
        self.life -= dt
        self.position += self.velocity * dt
        self.velocity *= 0.96

    def draw(self, surface: pygame.Surface) -> None:
        if self.life <= 0:
            return
        radius = max(1, round(4 * self.life / self.max_life))
        pygame.draw.circle(surface, self.color, self.position, radius)


@dataclass(slots=True)
class FloatingText:
    text: str
    position: Vector2
    life: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> None:
        self.life -= dt
        self.position.y -= 35.0 * dt

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if self.life <= 0:
            return
        rendered = font.render(self.text, True, self.color)
        blit_centered(surface, rendered, self.position)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cargo Panic single-conveyor campaign demo")
    parser.add_argument(
        "--model",
        default="hand_landmarker.task",
        help="Path to MediaPipe hand_landmarker.task",
    )
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument(
        "--mouse-only",
        action="store_true",
        help="Run without opening the webcam tracker",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional deterministic campaign seed",
    )
    return parser.parse_args()


def drain_latest(tracking_queue: object) -> dict | None:
    latest = None
    while True:
        try:
            latest = tracking_queue.get_nowait()
        except queue.Empty:
            return latest


def create_containers() -> list[ContainerZone]:
    margin = 28
    gap = 16
    width = (SCREEN_WIDTH - margin * 2 - gap * 3) // 4
    top = 553
    height = 140
    return [
        ContainerZone(
            name=name,
            rect=pygame.Rect(margin + index * (width + gap), top, width, height),
        )
        for index, name in enumerate(DESTINATIONS)
    ]


def create_rule_mapping(rule_type: str, rng: random.Random) -> dict[str, str]:
    destinations = list(DESTINATIONS)
    rng.shuffle(destinations)
    return dict(zip(ATTRIBUTE_VALUES[rule_type], destinations, strict=True))


def create_level_manifest(spec: LevelSpec, rng: random.Random) -> list[str]:
    values = ATTRIBUTE_VALUES[spec.rule_type]
    manifest = [values[index % len(values)] for index in range(spec.package_count)]
    rng.shuffle(manifest)
    return manifest


def spawn_package(
    package_id: int,
    rule_type: str,
    forced_value: str,
    rng: random.Random,
) -> Package:
    attributes = {
        attribute: rng.choice(values)
        for attribute, values in ATTRIBUTE_VALUES.items()
    }
    attributes[rule_type] = forced_value
    return Package(
        package_id=package_id,
        position=Vector2(-PACKAGE_WIDTH, BELT_Y),
        parcel_type=rng.choices(("BOX", "MAILER", "CRATE"), weights=(0.55, 0.27, 0.18), k=1)[0],
        color=attributes["COLOR"],
        weight=attributes["WEIGHT"],
        mark=attributes["MARK"],
        status=attributes["STATUS"],
    )


def nearest_package(
    packages: list[Package],
    position: Vector2,
    maximum_distance: float = 100.0,
) -> Package | None:
    candidates = [
        package
        for package in packages
        if package.alive
        and package.held_by is None
        and package.position.distance_to(position) <= maximum_distance
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda package: package.position.distance_squared_to(position))


def package_by_id(packages: list[Package], package_id: int | None) -> Package | None:
    if package_id is None:
        return None
    for package in packages:
        if package.package_id == package_id and package.alive:
            return package
    return None


def create_particles(
    particles: list[Particle],
    position: Vector2,
    color: tuple[int, int, int],
    count: int = 24,
) -> None:
    for _ in range(count):
        angle = random.uniform(0.0, math.tau)
        speed = random.uniform(80.0, 250.0)
        life = random.uniform(0.28, 0.58)
        particles.append(
            Particle(
                position=position.copy(),
                velocity=Vector2(math.cos(angle), math.sin(angle)) * speed,
                life=life,
                max_life=life,
                color=color,
            )
        )


def draw_warehouse_background(
    surface: pygame.Surface,
    now: float,
    belt_speed: float,
) -> None:
    surface.fill(BACKGROUND)

    pygame.draw.rect(surface, (27, 34, 46), pygame.Rect(0, 0, SCREEN_WIDTH, 540))
    for x in range(0, SCREEN_WIDTH, 128):
        pygame.draw.line(surface, (36, 44, 58), (x, 0), (x, 540), 2)
    for y in range(0, 540, 96):
        pygame.draw.line(surface, (31, 39, 52), (0, y), (SCREEN_WIDTH, y), 1)

    for x in (95, 395, 695, 995):
        pygame.draw.rect(surface, (69, 78, 90), pygame.Rect(x, 7, 170, 11), border_radius=4)
        pygame.draw.rect(surface, (232, 226, 183), pygame.Rect(x + 12, 10, 146, 5), border_radius=3)
        glow = pygame.Surface((220, 80), pygame.SRCALPHA)
        pygame.draw.polygon(glow, (242, 231, 184, 18), ((35, 0), (185, 0), (220, 80), (0, 80)))
        surface.blit(glow, (x - 25, 18))

    for x in (10, 625, 1250):
        pygame.draw.rect(surface, (52, 61, 75), pygame.Rect(x, 138, 20, 402))
        pygame.draw.rect(surface, ACCENT, pygame.Rect(x, 500, 20, 14))

    belt_rect = pygame.Rect(0, BELT_Y - BELT_HEIGHT // 2, SCREEN_WIDTH, BELT_HEIGHT)
    pygame.draw.rect(surface, (19, 24, 33), belt_rect.move(0, 8))
    pygame.draw.rect(surface, (34, 40, 51), belt_rect)

    top_rail = pygame.Rect(0, belt_rect.top - 8, SCREEN_WIDTH, 13)
    bottom_rail = pygame.Rect(0, belt_rect.bottom - 5, SCREEN_WIDTH, 13)
    pygame.draw.rect(surface, (92, 101, 116), top_rail)
    pygame.draw.rect(surface, (92, 101, 116), bottom_rail)
    pygame.draw.line(surface, (147, 155, 168), (0, top_rail.top + 2), (SCREEN_WIDTH, top_rail.top + 2), 2)
    pygame.draw.line(surface, (147, 155, 168), (0, bottom_rail.top + 2), (SCREEN_WIDTH, bottom_rail.top + 2), 2)

    slat_offset = int((now * belt_speed) % 58)
    for x in range(-58, SCREEN_WIDTH + 58, 58):
        slat_x = x + slat_offset
        pygame.draw.rect(
            surface,
            (47, 54, 68),
            pygame.Rect(slat_x, belt_rect.top + 10, 42, belt_rect.height - 20),
            border_radius=6,
        )
        pygame.draw.line(
            surface,
            (61, 70, 85),
            (slat_x + 8, belt_rect.top + 16),
            (slat_x + 8, belt_rect.bottom - 16),
            2,
        )

    for x in range(95, SCREEN_WIDTH, 190):
        arrow_x = x + int((now * belt_speed * 0.55) % 95)
        pygame.draw.polygon(
            surface,
            ACCENT,
            ((arrow_x - 16, BELT_Y - 10), (arrow_x + 7, BELT_Y), (arrow_x - 16, BELT_Y + 10)),
        )

    plate = pygame.Rect(34, belt_rect.top + 15, 190, 34)
    pygame.draw.rect(surface, (19, 24, 33), plate, border_radius=7)
    pygame.draw.rect(surface, ACCENT, plate, 2, border_radius=7)

    pygame.draw.rect(surface, (23, 29, 38), pygame.Rect(0, 540, SCREEN_WIDTH, 180))
    for x in range(-20, SCREEN_WIDTH + 80, 80):
        pygame.draw.polygon(
            surface,
            (177, 127, 43),
            ((x, 540), (x + 34, 540), (x + 4, 565), (x - 30, 565)),
        )


def draw_top_hud(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    spec: LevelSpec,
    level_index: int,
    mapping: dict[str, str],
    resolved: int,
    correct: int,
    level_score: int,
    campaign_score: int,
    combo: int,
) -> None:
    rule_panel = pygame.Rect(18, 18, 782, 154)
    status_panel = pygame.Rect(818, 18, 444, 154)
    draw_panel(surface, rule_panel)
    draw_panel(surface, status_panel)

    eyebrow = fonts["tiny_bold"].render(
        f"CONTRACT {level_index + 1:02d}/{len(LEVELS):02d}  •  {spec.title}",
        True,
        ACCENT,
    )
    surface.blit(eyebrow, (36, 31))
    surface.blit(fonts["title"].render(f"SORT BY {spec.rule_type}", True, INK), (35, 52))

    values = ATTRIBUTE_VALUES[spec.rule_type]
    for index, value in enumerate(values):
        destination = mapping[value]
        x = 37 + (index % 2) * 365
        y = 97 + (index // 2) * 31
        color = DESTINATION_COLORS[destination]
        pygame.draw.circle(surface, color, (x + 7, y + 8), 6)
        surface.blit(
            fonts["small_bold"].render(f"{value}  →  {destination}", True, (224, 229, 239)),
            (x + 20, y - 2),
        )

    progress_label = fonts["small_bold"].render(
        f"BATCH {min(resolved, spec.package_count)}/{spec.package_count}",
        True,
        INK,
    )
    surface.blit(progress_label, (838, 31))

    progress_rect = pygame.Rect(838, 57, 404, 14)
    pygame.draw.rect(surface, (16, 21, 29), progress_rect, border_radius=7)
    progress = min(1.0, resolved / max(spec.package_count, 1))
    fill_rect = progress_rect.copy()
    fill_rect.width = round(progress_rect.width * progress)
    if fill_rect.width > 0:
        pygame.draw.rect(surface, SUCCESS, fill_rect, border_radius=7)
    pygame.draw.rect(surface, (71, 84, 108), progress_rect, 2, border_radius=7)

    score_lines = (
        (f"QUALITY  {correct}/{spec.required_correct}", SUCCESS if correct >= spec.required_correct else INK),
        (f"LEVEL SCORE  {level_score}", INK),
        (f"TOTAL  {campaign_score + level_score}", INK),
        (f"COMBO  {combo}", ACCENT if combo >= 3 else MUTED),
    )
    for index, (text, color) in enumerate(score_lines):
        x = 838 + (index % 2) * 204
        y = 88 + (index // 2) * 34
        surface.blit(fonts["small_bold"].render(text, True, color), (x, y))

    for index in range(len(LEVELS)):
        dot_x = 1175 + index * 20
        dot_color = SUCCESS if index < level_index else (ACCENT if index == level_index else (77, 88, 108))
        pygame.draw.circle(surface, dot_color, (dot_x, 41), 6)


def draw_banner(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: tuple[int, int, int] = INK,
) -> None:
    rendered = font.render(text, True, color)
    rect = rendered.get_rect(center=(SCREEN_WIDTH // 2, 515))
    background = rect.inflate(34, 17)
    pygame.draw.rect(surface, (20, 26, 36), background, border_radius=10)
    pygame.draw.rect(surface, (80, 96, 128), background, 2, border_radius=10)
    surface.blit(rendered, rect)


def draw_overlay(surface: pygame.Surface, alpha: int = 190) -> None:
    overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
    overlay.fill((5, 8, 14, alpha))
    surface.blit(overlay, (0, 0))


def draw_menu(surface: pygame.Surface, fonts: dict[str, pygame.font.Font], mouse_only: bool) -> None:
    draw_overlay(surface, 205)
    card = pygame.Rect(270, 118, 740, 494)
    draw_panel(surface, card, fill=(20, 26, 36), border=(76, 92, 124), radius=20)

    blit_centered(surface, fonts["hero"].render("CARGO PANIC", True, INK), (SCREEN_WIDTH // 2, 182))
    blit_centered(surface, fonts["subtitle"].render("QUALITY CONTROL DEMO", True, ACCENT), (SCREEN_WIDTH // 2, 229))

    lines = (
        "One conveyor. Four complete contracts. No rule changes mid-level.",
        "Close a hand over a parcel to grab it. Open the hand over a bay to drop.",
        "Each contract has a fixed batch and a quality requirement.",
        "Finish the entire batch before the next contract unlocks.",
    )
    for index, line in enumerate(lines):
        blit_centered(surface, fonts["body"].render(line, True, (220, 226, 238)), (SCREEN_WIDTH // 2, 302 + index * 39))

    control_text = "MOUSE MODE ACTIVE" if mouse_only else "WEBCAM + MOUSE FALLBACK"
    pill = pygame.Rect(480, 465, 320, 38)
    pygame.draw.rect(surface, (36, 45, 59), pill, border_radius=19)
    pygame.draw.rect(surface, (82, 100, 134), pill, 2, border_radius=19)
    blit_centered(surface, fonts["small_bold"].render(control_text, True, MUTED), pill.center)

    blit_centered(
        surface,
        fonts["title"].render("HOLD A CLOSED HAND OR PRESS SPACE", True, (114, 218, 255)),
        (SCREEN_WIDTH // 2, 555),
    )


def draw_level_intro(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    spec: LevelSpec,
    level_index: int,
    mapping: dict[str, str],
) -> None:
    draw_overlay(surface, 205)
    card = pygame.Rect(250, 105, 780, 510)
    draw_panel(surface, card, fill=(20, 26, 36), border=(77, 94, 127), radius=20)

    blit_centered(surface, fonts["tiny_bold"].render(f"CONTRACT {level_index + 1} OF {len(LEVELS)}", True, ACCENT), (SCREEN_WIDTH // 2, 145))
    blit_centered(surface, fonts["hero_small"].render(spec.title, True, INK), (SCREEN_WIDTH // 2, 194))
    blit_centered(surface, fonts["body"].render(spec.description, True, (216, 223, 236)), (SCREEN_WIDTH // 2, 239))

    objective = f"PROCESS {spec.package_count} PARCELS  •  DELIVER AT LEAST {spec.required_correct} CORRECTLY"
    blit_centered(surface, fonts["small_bold"].render(objective, True, SUCCESS), (SCREEN_WIDTH // 2, 285))

    values = ATTRIBUTE_VALUES[spec.rule_type]
    for index, value in enumerate(values):
        destination = mapping[value]
        row = pygame.Rect(360, 326 + index * 48, 560, 38)
        pygame.draw.rect(surface, (30, 37, 50), row, border_radius=8)
        pygame.draw.rect(surface, DESTINATION_COLORS[destination], row, 2, border_radius=8)
        surface.blit(fonts["small_bold"].render(value, True, INK), (380, row.y + 8))
        surface.blit(fonts["small_bold"].render("→", True, MUTED), (620, row.y + 8))
        surface.blit(fonts["small_bold"].render(destination, True, DESTINATION_COLORS[destination]), (680, row.y + 8))

    blit_centered(surface, fonts["title"].render("PRESS SPACE TO BEGIN", True, (114, 218, 255)), (SCREEN_WIDTH // 2, 577))


def draw_level_summary(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    spec: LevelSpec,
    level_index: int,
    correct: int,
    wrong: int,
    missed: int,
    level_score: int,
    passed: bool,
) -> None:
    draw_overlay(surface, 210)
    card = pygame.Rect(290, 110, 700, 500)
    border = SUCCESS if passed else DANGER
    draw_panel(surface, card, fill=(20, 26, 36), border=border, radius=20, border_width=3)

    heading = "CONTRACT PASSED" if passed else "CONTRACT FAILED"
    blit_centered(surface, fonts["hero_small"].render(heading, True, border), (SCREEN_WIDTH // 2, 172))
    blit_centered(surface, fonts["subtitle"].render(spec.title, True, INK), (SCREEN_WIDTH // 2, 217))

    accuracy = correct / max(spec.package_count, 1)
    metrics = (
        ("CORRECT", str(correct), SUCCESS),
        ("WRONG BAY", str(wrong), DANGER if wrong else MUTED),
        ("MISSED", str(missed), DANGER if missed else MUTED),
        ("ACCURACY", f"{accuracy:.0%}", INK),
        ("LEVEL SCORE", str(level_score), ACCENT),
        ("REQUIRED", f"{spec.required_correct}/{spec.package_count}", MUTED),
    )
    for index, (label, value, color) in enumerate(metrics):
        column = index % 3
        row = index // 3
        x = 405 + column * 235
        y = 305 + row * 103
        blit_centered(surface, fonts["tiny_bold"].render(label, True, MUTED), (x, y))
        blit_centered(surface, fonts["metric"].render(value, True, color), (x, y + 40))

    prompt = "PRESS SPACE FOR NEXT CONTRACT" if passed and level_index < len(LEVELS) - 1 else (
        "PRESS SPACE FOR FINAL REPORT" if passed else "PRESS SPACE TO RETRY THIS CONTRACT"
    )
    blit_centered(surface, fonts["title"].render(prompt, True, (114, 218, 255)), (SCREEN_WIDTH // 2, 566))


def draw_campaign_results(
    surface: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    score: int,
    total_correct: int,
    total_wrong: int,
    total_missed: int,
    best_combo: int,
) -> None:
    draw_overlay(surface, 215)
    card = pygame.Rect(270, 90, 740, 540)
    draw_panel(surface, card, fill=(20, 26, 36), border=SUCCESS, radius=22, border_width=3)

    total = max(total_correct + total_wrong + total_missed, 1)
    ratio = total_correct / total
    if ratio >= 0.92:
        grade = "S"
        verdict = "MASTER DISPATCHER"
    elif ratio >= 0.84:
        grade = "A"
        verdict = "CERTIFIED DISPATCHER"
    elif ratio >= 0.74:
        grade = "B"
        verdict = "SHIFT APPROVED"
    else:
        grade = "C"
        verdict = "TRAINING COMPLETE"

    blit_centered(surface, fonts["tiny_bold"].render("CAMPAIGN COMPLETE", True, ACCENT), (SCREEN_WIDTH // 2, 130))
    blit_centered(surface, fonts["grade"].render(grade, True, SUCCESS), (SCREEN_WIDTH // 2, 230))
    blit_centered(surface, fonts["subtitle"].render(verdict, True, INK), (SCREEN_WIDTH // 2, 303))

    metrics = (
        ("TOTAL SCORE", str(score)),
        ("ACCURACY", f"{ratio:.0%}"),
        ("CORRECT", str(total_correct)),
        ("WRONG", str(total_wrong)),
        ("MISSED", str(total_missed)),
        ("BEST COMBO", str(best_combo)),
    )
    for index, (label, value) in enumerate(metrics):
        x = 405 + (index % 3) * 235
        y = 385 + (index // 3) * 85
        blit_centered(surface, fonts["tiny_bold"].render(label, True, MUTED), (x, y))
        blit_centered(surface, fonts["metric"].render(value, True, INK), (x, y + 34))

    blit_centered(surface, fonts["title"].render("PRESS SPACE TO START A NEW CAMPAIGN", True, (114, 218, 255)), (SCREEN_WIDTH // 2, 585))



def main() -> None:
    """Run the playable Pygame build backed by the OOP domain model."""
    parser = argparse.ArgumentParser(description="Cargo Panic OOP playable build")
    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Enable MediaPipe hand tracking. Mouse mode is the default.",
    )
    parser.add_argument(
        "--mouse-only",
        action="store_true",
        help="Explicitly disable webcam tracking (kept for compatibility).",
    )
    parser.add_argument(
        "--model",
        default="hand_landmarker.task",
        help="Path to MediaPipe hand_landmarker.task when --webcam is used.",
    )
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--smoke-test-frames",
        type=int,
        default=0,
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args()
    webcam_enabled = bool(args.webcam and not args.mouse_only)

    campaign_seed = args.seed if args.seed is not None else random.randrange(1, 2**31)
    rng = random.Random(campaign_seed)

    context: mp.context.BaseContext | None = None
    tracking_queue: object | None = None
    stop_event: object | None = None
    tracker: mp.Process | None = None

    if webcam_enabled:
        from pathlib import Path
        from infrastructure.vision.tracking_worker import vision_worker

        model_path = Path(args.model)
        if not model_path.is_absolute():
            model_path = Path(__file__).resolve().parent / model_path

        context = mp.get_context("spawn")
        tracking_queue = context.Queue(maxsize=2)
        stop_event = context.Event()
        tracker = context.Process(
            target=vision_worker,
            args=(tracking_queue, stop_event, str(model_path), args.camera),
            name="cargo-panic-vision",
        )
        tracker.start()

    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("Cargo Panic — OOP Persistent Tracking Build")
    clock = pygame.time.Clock()

    fonts = {
        "hero": load_font(66, True),
        "grade": load_font(116, True),
        "hero_small": load_font(48, True),
        "subtitle": load_font(28, True),
        "title": load_font(25, True),
        "body": load_font(23),
        "metric": load_font(38, True),
        "small_bold": load_font(18, True),
        "small": load_font(18),
        "tiny_bold": load_font(14, True),
        "tiny": load_font(14),
    }

    containers = create_containers()
    domain_zones = [
        DropZone(
            zone_id=f"{zone.name.lower()}-zone",
            destination=zone.name,
            left=float(zone.rect.left),
            top=float(zone.rect.top),
            right=float(zone.rect.right),
            bottom=float(zone.rect.bottom),
        )
        for zone in containers
    ]

    hands: dict[str, HandController] = {}
    package_views: dict[int, Package] = {}
    particles: list[Particle] = []
    floating_texts: list[FloatingText] = []

    state = "menu"
    current_level_index = 0
    rule_mapping: dict[str, str] = create_rule_mapping(LEVELS[0].rule_type, rng)
    manifest: list[str] = []

    campaign_score = 0
    campaign_correct = 0
    campaign_wrong = 0
    campaign_missed = 0
    best_combo = 0

    level_score = 0
    level_correct = 0
    level_wrong = 0
    level_missed = 0
    level_spawned = 0
    level_resolved = 0
    combo = 0
    next_package_id = 1
    spawn_timer = 0.0

    banner = ""
    banner_until = 0.0
    banner_color = INK
    tracking_fps = 0.0
    fatal_error: str | None = None
    gesture_start_since: float | None = None
    frame_count = 0

    def create_runtime_world(speed: float) -> GameWorld:
        game_world = GameWorld()
        game_world.add_conveyor(
            LinearConveyor(
                conveyor_id="primary",
                center_y=float(BELT_Y),
                speed=speed,
                left_bound=-float(PACKAGE_WIDTH),
                right_bound=float(SCREEN_WIDTH + PACKAGE_WIDTH),
                reattach_duration=0.28,
            )
        )
        for player_id in ("Mouse", "Left", "Right", "Hand"):
            game_world.add_player(PlayerInteractor(player_id, Vec2(0.0, 0.0)))
        return game_world

    world = create_runtime_world(LEVELS[0].belt_speed)

    gc.disable()

    def spec() -> LevelSpec:
        return LEVELS[current_level_index]

    def ensure_player(player_id: str, position: Vector2 | None = None) -> PlayerInteractor:
        try:
            return world.interactions.get_player(player_id)
        except KeyError:
            point = position or Vector2(0.0, 0.0)
            player = PlayerInteractor(player_id, Vec2(float(point.x), float(point.y)))
            world.add_player(player)
            return player

    def show_banner(
        text: str,
        duration: float = 1.0,
        color: tuple[int, int, int] = INK,
    ) -> None:
        nonlocal banner, banner_until, banner_color
        banner = text
        banner_until = time.perf_counter() + duration
        banner_color = color

    def sync_view(item_id: int) -> None:
        view = package_views.get(item_id)
        if view is None:
            return
        item = world.items.get(item_id)
        view.position.update(item.position.x, item.position.y)
        view.held_by = item.holder_id
        view.alive = item.active

    def clear_packages() -> None:
        package_views.clear()
        for hand in hands.values():
            hand.held_package_id = None

    def prepare_level(level_index: int) -> None:
        nonlocal current_level_index, rule_mapping, manifest, world
        nonlocal level_score, level_correct, level_wrong, level_missed
        nonlocal level_spawned, level_resolved, combo, spawn_timer, state

        current_level_index = level_index
        clear_packages()
        particles.clear()
        floating_texts.clear()
        level_score = 0
        level_correct = 0
        level_wrong = 0
        level_missed = 0
        level_spawned = 0
        level_resolved = 0
        combo = 0
        spawn_timer = 0.0
        world = create_runtime_world(spec().belt_speed)

        level_rng = random.Random(campaign_seed + (level_index + 1) * 1009)
        rule_mapping = create_rule_mapping(spec().rule_type, level_rng)
        manifest = create_level_manifest(spec(), level_rng)
        state = "level_intro"

    def reset_campaign() -> None:
        nonlocal campaign_seed, rng
        nonlocal campaign_score, campaign_correct, campaign_wrong, campaign_missed
        nonlocal best_combo, next_package_id

        campaign_seed = args.seed if args.seed is not None else random.randrange(1, 2**31)
        rng = random.Random(campaign_seed)
        campaign_score = 0
        campaign_correct = 0
        campaign_wrong = 0
        campaign_missed = 0
        best_combo = 0
        next_package_id = 1
        prepare_level(0)

    def begin_level() -> None:
        nonlocal state, spawn_timer
        state = "playing"
        spawn_timer = spec().spawn_interval
        show_banner("CONTRACT LIVE — COMPLETE THE FULL BATCH", 1.6, ACCENT)

    def record_outcome(item_id: int, outcome: str, destination: str | None = None) -> None:
        nonlocal level_score, level_correct, level_wrong, level_missed
        nonlocal level_resolved, combo, best_combo

        sync_view(item_id)
        view = package_views[item_id]
        level_resolved += 1

        if outcome == "correct":
            combo += 1
            best_combo = max(best_combo, combo)
            points = 100 + min(300, combo * 20)
            level_score += points
            level_correct += 1
            color = DESTINATION_COLORS[destination or "TRUCK"]
            create_particles(particles, view.position, color, 27)
            floating_texts.append(FloatingText(f"+{points}", view.position.copy(), 0.75, SUCCESS))
            show_banner(f"CORRECT ROUTE  •  COMBO {combo}", 0.75, SUCCESS)
        elif outcome == "wrong":
            combo = 0
            level_score = max(0, level_score - 75)
            level_wrong += 1
            create_particles(particles, view.position, DANGER, 22)
            floating_texts.append(FloatingText("WRONG BAY", view.position.copy(), 0.8, DANGER))
            show_banner("WRONG BAY — CHECK THE ACTIVE RULE", 1.0, DANGER)
        else:
            combo = 0
            level_score = max(0, level_score - 50)
            level_missed += 1
            floating_texts.append(FloatingText("MISSED", Vector2(SCREEN_WIDTH - 85, BELT_Y), 0.8, DANGER))
            show_banner("PARCEL MISSED", 0.8, DANGER)

    def grab_package(owner_id: str, position: Vector2) -> bool:
        player = ensure_player(owner_id, position)
        world.interactions.update_pointer(owner_id, Vec2(float(position.x), float(position.y)), time.perf_counter())
        item_id = world.interactions.grab_nearest(
            owner_id,
            time.perf_counter(),
            world.conveyors.values(),
            maximum_distance=100.0,
        )
        if item_id is None:
            return False
        if owner_id in hands:
            hands[owner_id].held_package_id = item_id
        return True

    def release_package(owner_id: str, position: Vector2) -> None:
        player = ensure_player(owner_id, position)
        item_id = player.held_item_id
        if item_id is None:
            if owner_id in hands:
                hands[owner_id].held_package_id = None
            return

        item = world.items.get(item_id)
        relevant_value = item.attribute(spec().rule_type)
        expected_destination = rule_mapping[relevant_value]
        result = world.interactions.release(
            owner_id,
            Vec2(float(position.x), float(position.y)),
            time.perf_counter(),
            domain_zones,
            world.conveyors,
            expected_destination=expected_destination,
        )
        if owner_id in hands:
            hands[owner_id].held_package_id = None
        if result is None:
            return

        outcome, released_id = result
        sync_view(released_id)
        if outcome in ("correct", "wrong"):
            dropped_zone = next(
                (zone for zone in containers if zone.rect.collidepoint(position)),
                None,
            )
            record_outcome(
                released_id,
                outcome,
                dropped_zone.name if dropped_zone else None,
            )
        elif outcome == "reattaching":
            # The item starts at the exact release point and eases back to the belt.
            show_banner("PARCEL REATTACHING — POSITION PRESERVED", 0.8, MUTED)
        else:
            show_banner("PARCEL RELEASED IN PLACE", 0.8, MUTED)

    def proceed_gate() -> None:
        nonlocal state, campaign_score, campaign_correct, campaign_wrong, campaign_missed
        if state == "menu":
            reset_campaign()
        elif state == "level_intro":
            begin_level()
        elif state == "level_summary":
            passed = level_correct >= spec().required_correct
            if passed:
                campaign_score += level_score + 500
                campaign_correct += level_correct
                campaign_wrong += level_wrong
                campaign_missed += level_missed
                if current_level_index == len(LEVELS) - 1:
                    state = "campaign_results"
                else:
                    prepare_level(current_level_index + 1)
            else:
                prepare_level(current_level_index)
        elif state == "campaign_results":
            state = "menu"

    running = True

    try:
        while running:
            dt = min(clock.tick(TARGET_FPS) / 1000.0, 0.05)
            now = time.perf_counter()
            frame_count += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        proceed_gate()
                    elif event.key == pygame.K_r and state == "level_summary":
                        prepare_level(current_level_index)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state == "playing":
                    grab_package("Mouse", Vector2(event.pos))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and state == "playing":
                    release_package("Mouse", Vector2(event.pos))

            mouse_position = Vector2(pygame.mouse.get_pos())
            mouse_player = ensure_player("Mouse", mouse_position)
            world.interactions.update_pointer(
                "Mouse",
                Vec2(float(mouse_position.x), float(mouse_position.y)),
                now,
            )

            if tracking_queue is not None:
                packet = drain_latest(tracking_queue)
                if packet is not None:
                    fatal = packet.get("fatal")
                    if fatal:
                        fatal_error = str(fatal)
                    tracking_fps = float(packet.get("tracking_fps", tracking_fps))
                    present_ids: set[str] = set()
                    for hand_packet in packet.get("hands", []):
                        hand_id = str(hand_packet["id"])
                        handedness = str(hand_packet.get("handedness", hand_id))
                        palm = hand_packet["palm"]
                        target = Vector2(float(palm[0]) * SCREEN_WIDTH, float(palm[1]) * SCREEN_HEIGHT)
                        target.x = min(max(target.x, 0.0), SCREEN_WIDTH)
                        target.y = min(max(target.y, 0.0), SCREEN_HEIGHT)
                        controller = hands.get(hand_id)
                        if controller is None:
                            controller = HandController(
                                hand_id=hand_id,
                                handedness=handedness,
                                target=target.copy(),
                                position=target.copy(),
                                last_seen=now,
                                state_since=now,
                            )
                            hands[hand_id] = controller
                            ensure_player(hand_id, target)
                        controller.target = target
                        controller.last_seen = now
                        controller.update_state(str(hand_packet.get("state", "neutral")), now)
                        present_ids.add(hand_id)

                    for hand_id, controller in hands.items():
                        if hand_id not in present_ids and now - controller.last_seen > TRACKING_TIMEOUT:
                            controller.update_state("neutral", now)
                            player = ensure_player(hand_id, controller.position)
                            if player.tracked:
                                world.interactions.tracking_lost(hand_id, now)

            for controller in hands.values():
                controller.smooth_position(dt)
                player = ensure_player(controller.hand_id, controller.position)

                if now - controller.last_seen > TRACKING_TIMEOUT:
                    # This check runs every game frame, even when the camera worker
                    # temporarily stops publishing packets. The held item is suspended
                    # at its exact last position instead of being reset to BELT_Y.
                    if player.tracked:
                        world.interactions.tracking_lost(controller.hand_id, now)
                    controller.held_package_id = player.held_item_id
                    continue

                point = Vec2(float(controller.position.x), float(controller.position.y))
                if not player.tracked:
                    world.interactions.tracking_recovered(controller.hand_id, point, now)
                else:
                    world.interactions.update_pointer(controller.hand_id, point, now)

                controller.held_package_id = player.held_item_id
                state_held_for = now - controller.state_since
                if state == "playing":
                    if (
                        controller.stable_state == "closed"
                        and state_held_for >= 0.08
                        and player.held_item_id is None
                        and now - controller.last_action_at >= 0.18
                    ):
                        if grab_package(controller.hand_id, controller.position):
                            controller.last_action_at = now
                    elif (
                        controller.stable_state == "open"
                        and state_held_for >= 0.08
                        and player.held_item_id is not None
                        and now - controller.last_action_at >= 0.18
                    ):
                        release_package(controller.hand_id, controller.position)
                        controller.last_action_at = now

            if state in ("menu", "level_intro", "level_summary", "campaign_results"):
                any_closed = any(
                    now - controller.last_seen <= TRACKING_TIMEOUT
                    and controller.stable_state == "closed"
                    for controller in hands.values()
                )
                if any_closed:
                    if gesture_start_since is None:
                        gesture_start_since = now
                    elif now - gesture_start_since >= 0.70:
                        proceed_gate()
                        gesture_start_since = None
                else:
                    gesture_start_since = None
            else:
                gesture_start_since = None

            if state == "playing":
                conveyor = world.conveyors["primary"]
                conveyor.speed = spec().belt_speed

                spawn_timer += dt
                active_items = world.items.active_items()
                active_belt_items = [
                    item
                    for item in active_items
                    if item.state in (ItemState.ON_CONVEYOR, ItemState.REATTACHING)
                ]
                spawn_clear = not any(item.position.x < 165.0 for item in active_belt_items)
                if (
                    level_spawned < spec().package_count
                    and spawn_timer >= spec().spawn_interval
                    and len(active_belt_items) < MAX_ACTIVE_PACKAGES
                    and spawn_clear
                ):
                    forced_value = manifest[level_spawned]
                    view = spawn_package(next_package_id, spec().rule_type, forced_value, rng)
                    item = PackageItem(
                        entity_id=next_package_id,
                        position=Vec2(float(view.position.x), float(view.position.y)),
                        attributes=ItemAttributes(
                            color=view.color,
                            weight=view.weight,
                            mark=view.mark,
                            status=view.status,
                            parcel_type=view.parcel_type,
                        ),
                    )
                    world.spawn_on_conveyor(item, "primary", now)
                    package_views[next_package_id] = view
                    next_package_id += 1
                    level_spawned += 1
                    spawn_timer -= spec().spawn_interval

                missed_ids = world.update(dt, now)
                for item_id in missed_ids:
                    if item_id in package_views:
                        sync_view(item_id)
                        record_outcome(item_id, "missed")

                for item in world.items.items():
                    if item.entity_id in package_views:
                        sync_view(item.entity_id)

                if level_resolved >= spec().package_count and not world.items.active_items():
                    state = "level_summary"
                    for hand in hands.values():
                        hand.held_package_id = None
            else:
                # Resolve a prolonged hand-tracking loss even while overlays are shown.
                world.interactions.update(now)

            for particle in particles:
                particle.update(dt)
            particles = [particle for particle in particles if particle.life > 0]

            for floating in floating_texts:
                floating.update(dt)
            floating_texts = [floating for floating in floating_texts if floating.life > 0]

            current_speed = spec().belt_speed if state in ("playing", "level_intro", "level_summary") else 64.0
            draw_warehouse_background(screen, now, current_speed)

            belt_label = fonts["small_bold"].render("PRIMARY CONVEYOR 01", True, (228, 232, 240))
            screen.blit(belt_label, (53, BELT_Y - BELT_HEIGHT // 2 + 23))

            if state not in ("menu", "campaign_results"):
                draw_top_hud(
                    screen,
                    fonts,
                    spec(),
                    current_level_index,
                    rule_mapping,
                    level_resolved,
                    level_correct,
                    level_score,
                    campaign_score,
                    combo,
                )

            hovered_zones: set[str] = set()
            for controller in hands.values():
                if now - controller.last_seen <= TRACKING_TIMEOUT:
                    for zone in containers:
                        if zone.rect.collidepoint(controller.position):
                            hovered_zones.add(zone.name)
            if mouse_player.held_item_id is not None:
                for zone in containers:
                    if zone.rect.collidepoint(pygame.mouse.get_pos()):
                        hovered_zones.add(zone.name)

            for zone in containers:
                zone.draw(screen, fonts["small_bold"], fonts["tiny_bold"], zone.name in hovered_zones)

            for item in world.items.active_items():
                view = package_views.get(item.entity_id)
                if view is not None:
                    view.draw(screen, fonts["tiny_bold"], fonts["tiny"], spec().rule_type)

            for particle in particles:
                particle.draw(screen)
            for floating in floating_texts:
                floating.draw(screen, fonts["small_bold"])

            for controller in hands.values():
                if now - controller.last_seen > TRACKING_TIMEOUT:
                    continue
                color = HAND_COLORS.get(controller.handedness, (150, 235, 160))
                cursor_radius = 18 if controller.stable_state == "closed" else 25
                pygame.draw.circle(screen, color, controller.position, cursor_radius, 5)
                if controller.stable_state == "closed":
                    pygame.draw.circle(screen, color, controller.position, 8)
                label = fonts["tiny_bold"].render(
                    f"{controller.handedness.upper()}  {controller.stable_state.upper()}",
                    True,
                    color,
                )
                screen.blit(label, (controller.position.x + 18, controller.position.y - 29))

            if now < banner_until and state == "playing":
                draw_banner(screen, fonts["small_bold"], banner, banner_color)

            tracking_label = (
                "MOUSE MODE — CLICK AND DRAG"
                if not webcam_enabled
                else f"TRACKING {tracking_fps:.1f} FPS  •  HANDS {sum(now - hand.last_seen <= TRACKING_TIMEOUT for hand in hands.values())}/2"
            )
            screen.blit(fonts["tiny_bold"].render(tracking_label, True, MUTED), (955, 699))

            if fatal_error:
                error = fonts["tiny_bold"].render(f"{fatal_error} — mouse controls remain available.", True, DANGER)
                screen.blit(error, (20, 699))

            if state == "menu":
                draw_menu(screen, fonts, not webcam_enabled)
            elif state == "level_intro":
                draw_level_intro(screen, fonts, spec(), current_level_index, rule_mapping)
            elif state == "level_summary":
                draw_level_summary(
                    screen,
                    fonts,
                    spec(),
                    current_level_index,
                    level_correct,
                    level_wrong,
                    level_missed,
                    level_score,
                    level_correct >= spec().required_correct,
                )
            elif state == "campaign_results":
                draw_campaign_results(
                    screen,
                    fonts,
                    campaign_score,
                    campaign_correct,
                    campaign_wrong,
                    campaign_missed,
                    best_combo,
                )

            pygame.display.flip()

            if args.smoke_test_frames > 0 and frame_count >= args.smoke_test_frames:
                running = False

    finally:
        if stop_event is not None:
            stop_event.set()
        if tracker is not None:
            tracker.join(timeout=2.0)
            if tracker.is_alive():
                tracker.terminate()
                tracker.join(timeout=1.0)
        if tracking_queue is not None:
            tracking_queue.close()
            tracking_queue.join_thread()

        pygame.quit()
        gc.enable()
        gc.collect()


if __name__ == "__main__":
    mp.freeze_support()
    main()
