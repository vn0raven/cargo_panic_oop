from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from core.config import INK, MUTED, PANEL, PANEL_BORDER


@dataclass(slots=True)
class ScannerConsole:
    rect: pygame.Rect

    def draw(
        self,
        surface: pygame.Surface,
        fonts: dict[str, pygame.font.Font],
        active: bool,
        progress: float,
    ) -> None:
        pygame.draw.rect(surface, PANEL, self.rect, border_radius=12)
        border = (92, 214, 235) if active else PANEL_BORDER
        pygame.draw.rect(surface, border, self.rect, 3, border_radius=12)

        title = fonts["small"].render("LABEL SCANNER", True, INK)
        surface.blit(title, (self.rect.x + 14, self.rect.y + 9))
        hint = fonts["tiny"].render("Hover damaged cargo + hold SPACE", True, MUTED)
        surface.blit(hint, (self.rect.x + 14, self.rect.y + 34))

        scan_rect = pygame.Rect(self.rect.x + 14, self.rect.bottom - 18, self.rect.width - 28, 8)
        pygame.draw.rect(surface, (41, 49, 63), scan_rect, border_radius=4)
        fill = scan_rect.copy()
        fill.width = round(scan_rect.width * max(0.0, min(1.0, progress)))
        pygame.draw.rect(surface, (92, 214, 235), fill, border_radius=4)

        if active:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 90.0)
            line_x = self.rect.x + 14 + round((self.rect.width - 28) * pulse)
            pygame.draw.line(surface, (180, 246, 255), (line_x, self.rect.y + 8), (line_x, self.rect.bottom - 24), 2)
