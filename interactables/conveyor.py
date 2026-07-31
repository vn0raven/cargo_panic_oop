from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from core.config import BELT_DARK, BELT_LIGHT, BELT_RECT, INK, MUTED
from core.enums import PackageKind, PackageState
from entities.package import CargoPackage


@dataclass(slots=True)
class ConveyorBelt:
    base_speed: float
    visual_offset: float = 0.0
    surge_multiplier: float = 1.0

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(BELT_RECT)

    @property
    def speed(self) -> float:
        return self.base_speed * self.surge_multiplier

    def update(self, packages: list[CargoPackage], dt: float) -> None:
        self.visual_offset = (self.visual_offset + self.speed * dt) % 84
        for package in packages:
            if package.state is not PackageState.ON_BELT:
                continue
            kind_factor = 1.08 if package.kind is PackageKind.SMALL else 0.92 if package.kind is PackageKind.HEAVY else 1.0
            package.position.x += self.speed * kind_factor * dt

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font]) -> None:
        rect = self.rect
        pygame.draw.rect(surface, (17, 22, 30), rect.move(0, 9), border_radius=18)
        pygame.draw.rect(surface, BELT_DARK, rect, border_radius=18)
        inner = rect.inflate(-20, -34)
        pygame.draw.rect(surface, BELT_LIGHT, inner, border_radius=12)

        stripe_width = 42
        start = -stripe_width * 2 + int(self.visual_offset)
        for x in range(start, rect.right + stripe_width, stripe_width * 2):
            points = (
                (x, inner.y),
                (x + stripe_width, inner.y),
                (x + stripe_width * 2, inner.bottom),
                (x + stripe_width, inner.bottom),
            )
            pygame.draw.polygon(surface, (56, 64, 77), points)

        for x in range(30, rect.right, 84):
            pygame.draw.circle(surface, (26, 31, 40), (x, rect.bottom - 13), 10)
            pygame.draw.circle(surface, (88, 99, 116), (x, rect.bottom - 13), 5)

        label = fonts["small"].render("INBOUND CONVEYOR  •  KEEP LINE CLEAR", True, MUTED)
        surface.blit(label, (28, rect.y + 10))

        danger_x = rect.right - 100
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 180.0)
        danger_color = (round(140 + 100 * pulse), 68, 68)
        pygame.draw.rect(surface, danger_color, pygame.Rect(danger_x, rect.y + 5, 90, rect.height - 10), 3, border_radius=11)
        warning = fonts["tiny"].render("MISS ZONE", True, INK)
        surface.blit(warning, warning.get_rect(midtop=(danger_x + 45, rect.y + 14)))
