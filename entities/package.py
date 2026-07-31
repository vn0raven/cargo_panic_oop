from __future__ import annotations

from dataclasses import dataclass, field
import math

import pygame
from pygame.math import Vector2

from core.config import (
    DESTINATION_COLORS,
    INK,
    MUTED,
    PACKAGE_BODY_COLORS,
    PACKAGE_SIZE,
    TAG_COLORS,
)
from core.enums import Destination, HandlingTag, PackageKind, PackageState


def draw_destination_symbol(
    surface: pygame.Surface,
    destination: Destination,
    center: tuple[int, int],
    color: tuple[int, int, int],
    size: int = 12,
    width: int = 3,
) -> None:
    x, y = center
    if destination is Destination.NORTHPORT:
        pygame.draw.polygon(
            surface,
            color,
            ((x, y - size), (x - size, y + size), (x + size, y + size)),
            width,
        )
    elif destination is Destination.EASTVALE:
        pygame.draw.circle(surface, color, center, size, width)
    else:
        pygame.draw.rect(
            surface,
            color,
            pygame.Rect(x - size, y - size, size * 2, size * 2),
            width,
        )


@dataclass(slots=True)
class CargoPackage:
    package_id: int
    destination: Destination
    kind: PackageKind
    tag: HandlingTag
    position: Vector2
    spawned_at: float
    state: PackageState = PackageState.ON_BELT
    label_revealed: bool = True
    scan_progress: float = 0.0
    held_offset: Vector2 = field(default_factory=Vector2)
    last_position: Vector2 = field(default_factory=Vector2)
    peak_drag_speed: float = 0.0
    rejected_until: float = 0.0

    @property
    def width(self) -> int:
        if self.kind is PackageKind.SMALL:
            return 88
        if self.kind is PackageKind.HEAVY:
            return 128
        return PACKAGE_SIZE[0]

    @property
    def height(self) -> int:
        if self.kind is PackageKind.SMALL:
            return 62
        if self.kind is PackageKind.HEAVY:
            return 88
        return PACKAGE_SIZE[1]

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            round(self.position.x - self.width / 2),
            round(self.position.y - self.height / 2),
            self.width,
            self.height,
        )

    @property
    def urgent_deadline(self) -> float | None:
        if self.tag is HandlingTag.REFRIGERATED:
            return 10.5
        if self.tag is HandlingTag.EXPRESS:
            return 7.0
        return None

    def age(self, now: float) -> float:
        return max(0.0, now - self.spawned_at)

    def update_drag(self, mouse_pos: tuple[int, int], dt: float) -> None:
        target = Vector2(mouse_pos) - self.held_offset
        previous = self.position.copy()
        if self.kind is PackageKind.HEAVY:
            alpha = 1.0 - math.exp(-8.5 * dt)
            self.position = self.position.lerp(target, alpha)
        else:
            self.position = target
        if dt > 0:
            self.peak_drag_speed = max(
                self.peak_drag_speed,
                self.position.distance_to(previous) / dt,
            )
        self.last_position = previous

    def reset_drag_metrics(self) -> None:
        self.peak_drag_speed = 0.0
        self.last_position = self.position.copy()

    def draw(
        self,
        surface: pygame.Surface,
        fonts: dict[str, pygame.font.Font],
        now: float,
        highlight: bool = False,
    ) -> None:
        rect = self.rect
        shadow = rect.move(7, 7)
        pygame.draw.rect(surface, (7, 10, 15), shadow, border_radius=10)

        body = PACKAGE_BODY_COLORS[self.kind.value]
        if self.kind is PackageKind.SMALL:
            pygame.draw.rect(surface, body, rect, border_radius=15)
            pygame.draw.polygon(
                surface,
                (196, 187, 163),
                ((rect.x + 4, rect.y + 7), (rect.centerx, rect.centery), (rect.right - 4, rect.y + 7)),
            )
        elif self.kind is PackageKind.HEAVY:
            pygame.draw.rect(surface, body, rect, border_radius=5)
            for x in range(rect.x + 9, rect.right, 22):
                pygame.draw.line(surface, (86, 55, 35), (x, rect.y + 5), (x, rect.bottom - 5), 3)
            for y in (rect.y + 10, rect.bottom - 13):
                pygame.draw.line(surface, (96, 61, 37), (rect.x + 4, y), (rect.right - 4, y), 4)
        else:
            pygame.draw.rect(surface, body, rect, border_radius=8)
            pygame.draw.line(surface, (147, 104, 63), (rect.centerx, rect.y + 3), (rect.centerx, rect.bottom - 3), 3)

        destination_color = DESTINATION_COLORS[self.destination.value]
        pygame.draw.rect(surface, destination_color, pygame.Rect(rect.x + 7, rect.y + 7, 12, rect.height - 14), border_radius=4)
        pygame.draw.rect(surface, (235, 224, 200), rect, 3, border_radius=8)

        label_rect = pygame.Rect(rect.x + 27, rect.y + 8, rect.width - 35, min(48, rect.height - 16))
        pygame.draw.rect(surface, (247, 247, 241), label_rect, border_radius=4)
        pygame.draw.rect(surface, (36, 39, 43), label_rect, 1, border_radius=4)

        tiny = fonts["tiny"]
        small = fonts["small"]
        package_code = tiny.render(f"CP-{self.package_id:04d}", True, (28, 30, 34))
        surface.blit(package_code, (label_rect.x + 5, label_rect.y + 3))

        if self.label_revealed:
            draw_destination_symbol(
                surface,
                self.destination,
                (label_rect.x + 14, label_rect.bottom - 13),
                destination_color,
                size=8,
                width=3,
            )
            name = tiny.render(self.destination.value.upper(), True, (28, 30, 34))
            surface.blit(name, (label_rect.x + 27, label_rect.bottom - 20))
        else:
            hidden = small.render("???", True, (64, 66, 71))
            surface.blit(hidden, hidden.get_rect(center=(label_rect.centerx, label_rect.centery + 8)))
            for offset in (0, 7, 14):
                pygame.draw.line(
                    surface,
                    (152, 93, 84),
                    (label_rect.x + 8, label_rect.y + 13 + offset),
                    (label_rect.right - 8, label_rect.y + 7 + offset),
                    3,
                )

        tag_color = TAG_COLORS[self.tag.value]
        tag_rect = pygame.Rect(rect.x + 6, rect.bottom - 22, min(rect.width - 12, 76), 17)
        pygame.draw.rect(surface, tag_color, tag_rect, border_radius=4)
        tag_text = tiny.render(self.tag.value.upper(), True, INK)
        surface.blit(tag_text, tag_text.get_rect(center=tag_rect.center))

        if self.state is PackageState.SCANNING:
            progress_rect = pygame.Rect(rect.x, rect.bottom + 5, rect.width, 8)
            pygame.draw.rect(surface, (35, 42, 54), progress_rect, border_radius=4)
            fill = progress_rect.copy()
            fill.width = round(progress_rect.width * min(1.0, self.scan_progress))
            pygame.draw.rect(surface, (96, 214, 235), fill, border_radius=4)
            scan_text = tiny.render("SCANNING", True, INK)
            surface.blit(scan_text, scan_text.get_rect(midbottom=(rect.centerx, progress_rect.y - 1)))

        if self.urgent_deadline is not None:
            remaining = self.urgent_deadline - self.age(now)
            if remaining < 5.0:
                urgency = max(0.0, min(1.0, remaining / 5.0))
                ring_color = (
                    round(244 - 30 * urgency),
                    round(83 + 115 * urgency),
                    round(83 + 20 * urgency),
                )
                pygame.draw.rect(surface, ring_color, rect.inflate(8, 8), 3, border_radius=12)
                countdown = tiny.render(f"{max(0.0, remaining):.1f}s", True, ring_color)
                surface.blit(countdown, countdown.get_rect(midtop=(rect.centerx, rect.bottom + 14)))

        if now < self.rejected_until:
            pygame.draw.rect(surface, (244, 89, 89), rect.inflate(10, 10), 4, border_radius=12)

        if highlight:
            pygame.draw.rect(surface, INK, rect.inflate(8, 8), 3, border_radius=12)

        kind_text = tiny.render(self.kind.value.upper(), True, MUTED)
        surface.blit(kind_text, kind_text.get_rect(midtop=(rect.centerx, rect.bottom + 26)))
