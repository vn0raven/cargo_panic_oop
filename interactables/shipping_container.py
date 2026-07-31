from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from core.config import DESTINATION_COLORS, INK, MUTED, PANEL_2
from core.enums import Destination
from entities.package import draw_destination_symbol


@dataclass(slots=True)
class ShippingContainer:
    destination: Destination
    rect: pygame.Rect
    closed_until: float = 0.0
    warning_until: float = 0.0

    def is_closed(self, now: float) -> bool:
        return now < self.closed_until

    def contains(self, point: tuple[int, int]) -> bool:
        return self.rect.collidepoint(point)

    def draw(
        self,
        surface: pygame.Surface,
        fonts: dict[str, pygame.font.Font],
        now: float,
        highlighted: bool = False,
    ) -> None:
        color = DESTINATION_COLORS[self.destination.value]
        rect = self.rect
        pygame.draw.rect(surface, (7, 10, 15), rect.move(0, 6), border_radius=15)
        pygame.draw.rect(surface, PANEL_2, rect, border_radius=15)

        title_bar = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, 35)
        pygame.draw.rect(surface, color, title_bar, border_radius=8)
        title = fonts["medium"].render(self.destination.value.upper(), True, INK)
        surface.blit(title, title.get_rect(center=title_bar.center))

        bay = pygame.Rect(rect.x + 14, rect.y + 52, rect.width - 28, rect.height - 66)
        pygame.draw.rect(surface, (43, 51, 65), bay, border_radius=9)
        for y in range(bay.y + 8, bay.bottom, 13):
            pygame.draw.line(surface, (62, 72, 88), (bay.x + 6, y), (bay.right - 6, y), 2)

        draw_destination_symbol(surface, self.destination, (rect.centerx, rect.centery + 30), color, 25, 6)

        if self.is_closed(now):
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((20, 22, 28, 185))
            surface.blit(overlay, rect.topleft)
            for x in range(rect.x - rect.height, rect.right, 32):
                pygame.draw.line(surface, (224, 74, 74), (x, rect.bottom), (x + rect.height, rect.y), 8)
            closed = fonts["large"].render("CLOSED", True, INK)
            surface.blit(closed, closed.get_rect(center=rect.center))
            remaining = max(0.0, self.closed_until - now)
            timer = fonts["small"].render(f"Reopens in {remaining:.1f}s", True, INK)
            surface.blit(timer, timer.get_rect(midtop=(rect.centerx, rect.centery + 30)))
        elif now < self.warning_until:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 100.0)
            warning_color = (255, round(120 + 100 * pulse), 70)
            pygame.draw.rect(surface, warning_color, rect, 6, border_radius=15)
            text = fonts["small"].render("CLOSING SOON", True, warning_color)
            surface.blit(text, text.get_rect(midbottom=(rect.centerx, rect.y - 5)))
        else:
            border = INK if highlighted else color
            width = 6 if highlighted else 3
            pygame.draw.rect(surface, border, rect, width, border_radius=15)

        instruction = fonts["tiny"].render("DROP MATCHING CARGO", True, MUTED)
        surface.blit(instruction, instruction.get_rect(midbottom=(rect.centerx, rect.bottom - 5)))
