from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import pygame

from .constants import (
    ACCENT,
    BACKGROUND,
    BACKGROUND_2,
    DANGER,
    DESTINATION_COLORS,
    DIM,
    FOCUS,
    INK,
    MUTED,
    PACKAGE_COLORS,
    PANEL,
    PANEL_2,
    PANEL_BORDER,
    STATUS_COLORS,
    SUCCESS,
    WARNING,
    WEIGHT_LABELS,
)
from .models import Parcel


@dataclass(slots=True)
class Theme:
    high_contrast: bool = False

    @property
    def background(self) -> tuple[int, int, int]:
        return (3, 5, 9) if self.high_contrast else BACKGROUND

    @property
    def background_2(self) -> tuple[int, int, int]:
        return (12, 16, 25) if self.high_contrast else BACKGROUND_2

    @property
    def panel(self) -> tuple[int, int, int]:
        return (12, 16, 23) if self.high_contrast else PANEL

    @property
    def panel_2(self) -> tuple[int, int, int]:
        return (20, 26, 38) if self.high_contrast else PANEL_2

    @property
    def border(self) -> tuple[int, int, int]:
        return (138, 157, 190) if self.high_contrast else PANEL_BORDER

    @property
    def ink(self) -> tuple[int, int, int]:
        return (255, 255, 255) if self.high_contrast else INK

    @property
    def muted(self) -> tuple[int, int, int]:
        return (204, 214, 233) if self.high_contrast else MUTED

    @property
    def dim(self) -> tuple[int, int, int]:
        return (150, 164, 190) if self.high_contrast else DIM


class FontBook:
    def __init__(self) -> None:
        self._cache: dict[tuple[int, bool], pygame.font.Font] = {}

    def get(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self._cache:
            font = pygame.font.SysFont("segoeui,arial", size, bold=bold)
            if font is None:
                font = pygame.font.Font(None, size)
            self._cache[key] = font
        return self._cache[key]


@dataclass(slots=True)
class Button:
    rect: pygame.Rect
    label: str
    action: Callable[[], None]
    kind: str = "primary"
    enabled: bool = True
    shortcut: str = ""

    def draw(
        self,
        surface: pygame.Surface,
        fonts: FontBook,
        theme: Theme,
        mouse_pos: tuple[int, int],
        focused: bool = False,
    ) -> None:
        hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        if not self.enabled:
            fill, border, text = theme.panel, theme.border, theme.dim
        elif self.kind == "primary":
            fill = (218, 145, 43) if hovered else ACCENT
            border = (255, 215, 137)
            text = (18, 22, 30)
        elif self.kind == "danger":
            fill = (180, 57, 66) if hovered else (137, 46, 56)
            border = DANGER
            text = theme.ink
        else:
            fill = (49, 62, 86) if hovered else theme.panel_2
            border = FOCUS if focused else theme.border
            text = theme.ink

        shadow = self.rect.move(0, 4)
        pygame.draw.rect(surface, (5, 7, 12), shadow, border_radius=12)
        pygame.draw.rect(surface, fill, self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect, 2 if not focused else 3, border_radius=12)
        label = fonts.get(20, True).render(self.label, True, text)
        surface.blit(label, label.get_rect(center=self.rect.center))
        if self.shortcut:
            hint = fonts.get(13, True).render(self.shortcut, True, text)
            surface.blit(hint, hint.get_rect(midright=(self.rect.right - 14, self.rect.centery)))

    def activate_at(self, point: tuple[int, int]) -> bool:
        if self.enabled and self.rect.collidepoint(point):
            self.action()
            return True
        return False


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    theme: Theme,
    *,
    fill: tuple[int, int, int] | None = None,
    border: tuple[int, int, int] | None = None,
    radius: int = 14,
    width: int = 2,
    shadow: bool = True,
) -> None:
    if shadow:
        pygame.draw.rect(surface, (4, 7, 12), rect.move(0, 5), border_radius=radius)
    pygame.draw.rect(surface, fill or theme.panel, rect, border_radius=radius)
    pygame.draw.rect(surface, border or theme.border, rect, width, border_radius=radius)


def draw_background(surface: pygame.Surface, theme: Theme, t: float) -> None:
    surface.fill(theme.background)
    # Layered warehouse wall bands.
    pygame.draw.rect(surface, theme.background_2, pygame.Rect(0, 0, surface.get_width(), 270))
    for y in range(0, 270, 54):
        pygame.draw.line(surface, (27, 35, 50), (0, y), (surface.get_width(), y), 1)
    for x in range(-120, surface.get_width() + 120, 160):
        offset = int((t * 8) % 160)
        pygame.draw.line(surface, (24, 31, 45), (x + offset, 0), (x + 80 + offset, 270), 1)
    # Ceiling lights.
    for x in (170, 640, 1110):
        glow = pygame.Surface((220, 110), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (255, 214, 140, 18), glow.get_rect())
        surface.blit(glow, (x - 110, -26))
        pygame.draw.rect(surface, (198, 204, 217), pygame.Rect(x - 45, 18, 90, 7), border_radius=3)


def draw_hazard_stripe(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.rect(surface, (34, 37, 43), rect)
    stripe = 26
    for x in range(rect.left - rect.height, rect.right + rect.height, stripe * 2):
        points = [
            (x, rect.bottom),
            (x + stripe, rect.bottom),
            (x + stripe + rect.height, rect.top),
            (x + rect.height, rect.top),
        ]
        pygame.draw.polygon(surface, (218, 161, 45), points)


def draw_conveyor(surface: pygame.Surface, rect: pygame.Rect, offset: float) -> None:
    pygame.draw.rect(surface, (15, 19, 27), rect)
    pygame.draw.rect(surface, (71, 80, 96), rect, 4)
    inner = rect.inflate(-20, -32)
    pygame.draw.rect(surface, (44, 50, 61), inner, border_radius=18)
    roller_width = 54
    shift = int(offset) % roller_width
    for x in range(inner.left - roller_width + shift, inner.right + roller_width, roller_width):
        roller = pygame.Rect(x, inner.top + 7, roller_width - 10, inner.height - 14)
        pygame.draw.rect(surface, (78, 87, 101), roller, border_radius=12)
        pygame.draw.line(surface, (111, 121, 137), (roller.left + 8, roller.top + 5), (roller.left + 8, roller.bottom - 5), 2)
    draw_hazard_stripe(surface, pygame.Rect(rect.left, rect.top, rect.width, 14))
    draw_hazard_stripe(surface, pygame.Rect(rect.left, rect.bottom - 14, rect.width, 14))


def draw_mark_icon(
    surface: pygame.Surface,
    mark: str,
    center: tuple[int, int],
    color: tuple[int, int, int],
    size: int,
    width: int = 3,
) -> None:
    x, y = center
    if mark == "CIRCLE":
        pygame.draw.circle(surface, color, center, size, width)
    elif mark == "TRIANGLE":
        pygame.draw.polygon(surface, color, ((x, y - size), (x - size, y + size), (x + size, y + size)), width)
    elif mark == "SQUARE":
        pygame.draw.rect(surface, color, pygame.Rect(x - size, y - size, size * 2, size * 2), width)
    else:
        pygame.draw.polygon(surface, color, ((x, y - size), (x + size, y), (x, y + size), (x - size, y)), width)


def draw_destination_icon(
    surface: pygame.Surface,
    name: str,
    center: tuple[int, int],
    color: tuple[int, int, int],
    scale: float = 1.0,
) -> None:
    x, y = center
    s = scale
    dark = (17, 22, 30)

    def rect(dx: float, dy: float, w: float, h: float) -> pygame.Rect:
        return pygame.Rect(round(x + dx * s), round(y + dy * s), round(w * s), round(h * s))

    if name == "TRUCK":
        pygame.draw.rect(surface, color, rect(-42, -14, 52, 27), border_radius=5)
        pygame.draw.polygon(
            surface,
            color,
            tuple(
                (round(x + px * s), round(y + py * s))
                for px, py in ((10, -10), (30, -10), (42, 4), (42, 13), (10, 13))
            ),
        )
        pygame.draw.rect(surface, INK, rect(21, -6, 12, 8), border_radius=2)
        for wheel_x in (-25, 29):
            pygame.draw.circle(surface, dark, (round(x + wheel_x * s), round(y + 17 * s)), max(4, round(7 * s)))
            pygame.draw.circle(surface, INK, (round(x + wheel_x * s), round(y + 17 * s)), max(2, round(3 * s)))
    elif name == "SHIP":
        pygame.draw.polygon(
            surface,
            color,
            tuple(
                (round(x + px * s), round(y + py * s))
                for px, py in ((-45, 1), (45, 1), (29, 20), (-31, 20))
            ),
        )
        pygame.draw.rect(surface, INK, rect(-16, -16, 36, 17), border_radius=3)
        pygame.draw.rect(surface, color, rect(-5, -28, 10, 12))
        pygame.draw.arc(surface, INK, rect(-34, 17, 28, 12), 0.2, math.pi - 0.2, 2)
        pygame.draw.arc(surface, INK, rect(5, 17, 28, 12), 0.2, math.pi - 0.2, 2)
    elif name == "PLANE":
        points = [(-45, 6), (-8, -2), (19, -24), (30, -22), (15, -1), (45, 7), (39, 15), (10, 8), (-7, 26), (-15, 24), (-8, 7), (-40, 14)]
        pygame.draw.polygon(surface, color, [(round(x + px * s), round(y + py * s)) for px, py in points])
    else:
        pygame.draw.rect(surface, color, rect(-35, -22, 70, 44), 5, border_radius=8)
        pygame.draw.rect(surface, INK, rect(-15, -9, 30, 22), border_radius=3)
        pygame.draw.line(surface, dark, (round(x - 10 * s), round(y - 3 * s)), (round(x + 10 * s), round(y + 6 * s)), max(2, round(4 * s)))


def _render_text(fonts: FontBook, text: str, size: int, color: tuple[int, int, int], bold: bool = False) -> pygame.Surface:
    return fonts.get(size, bold).render(text, True, color)


def draw_parcel(
    surface: pygame.Surface,
    parcel: Parcel,
    rule_type: str,
    fonts: FontBook,
    theme: Theme,
    *,
    selected: bool = False,
    suspended: bool = False,
) -> None:
    rect = pygame.Rect(round(parcel.x), round(parcel.y), parcel.width, parcel.height)
    if selected:
        glow = rect.inflate(16, 16)
        pygame.draw.rect(surface, (246, 181, 75, 40), glow, border_radius=16)
        pygame.draw.rect(surface, ACCENT, glow, 3, border_radius=16)
    shadow = rect.move(5, 7)
    pygame.draw.rect(surface, (4, 6, 10), shadow, border_radius=9)

    body = (185, 137, 83)
    pygame.draw.rect(surface, body, rect, border_radius=8)
    pygame.draw.rect(surface, (95, 64, 38), rect, 3, border_radius=8)
    pygame.draw.line(surface, (225, 183, 125), (rect.left + 7, rect.top + 8), (rect.right - 7, rect.top + 8), 2)

    # Routing tape remains visible for atmosphere, but only becomes dominant for COLOR.
    tape_color = PACKAGE_COLORS[parcel.attributes.color]
    tape_rect = pygame.Rect(rect.left + 8, rect.top + 15, 14, rect.height - 30)
    pygame.draw.rect(surface, tape_color, tape_rect, border_radius=4)
    if rule_type != "COLOR":
        muted_overlay = pygame.Surface(tape_rect.size, pygame.SRCALPHA)
        muted_overlay.fill((30, 30, 30, 92))
        surface.blit(muted_overlay, tape_rect.topleft)

    # Active attribute card.
    active = parcel.active_value(rule_type)
    card = pygame.Rect(rect.left + 28, rect.top + 13, rect.width - 37, 42)
    active_color = ACCENT
    if rule_type == "COLOR":
        active_color = PACKAGE_COLORS[active]
    elif rule_type == "STATUS":
        active_color = STATUS_COLORS[active]
    pygame.draw.rect(surface, (250, 246, 232), card, border_radius=6)
    pygame.draw.rect(surface, active_color, card, 3, border_radius=6)

    if rule_type == "MARK":
        draw_mark_icon(surface, active, (card.centerx, card.centery), (24, 29, 38), 13, 4)
    else:
        label = WEIGHT_LABELS.get(active, active)
        text = _render_text(fonts, label, 18 if len(label) <= 8 else 15, (26, 30, 38), True)
        surface.blit(text, text.get_rect(center=card.center))

    # Quiet metadata row.
    meta = f"#{parcel.parcel_id:03d}  {parcel.attributes.status[:3]}  {parcel.attributes.mark[:3]}"
    meta_surface = _render_text(fonts, meta, 11, (65, 54, 43), True)
    surface.blit(meta_surface, (rect.left + 29, rect.bottom - 23))

    if suspended:
        veil = pygame.Surface(rect.size, pygame.SRCALPHA)
        veil.fill((8, 12, 18, 155))
        surface.blit(veil, rect.topleft)
        paused = _render_text(fonts, "TRACKING HELD", 13, WARNING, True)
        surface.blit(paused, paused.get_rect(center=rect.center))


def draw_bay(
    surface: pygame.Surface,
    rect: pygame.Rect,
    name: str,
    fonts: FontBook,
    theme: Theme,
    *,
    hovered: bool = False,
    valid: bool | None = None,
    guided: bool = False,
    pulse: float = 0.0,
) -> None:
    color = DESTINATION_COLORS[name]
    border = color
    fill = theme.panel
    width = 2
    if hovered:
        width = 4
        if valid is True:
            border = SUCCESS
            fill = (28, 63, 49)
        elif valid is False:
            border = DANGER
            fill = (65, 35, 43)
    elif guided:
        width = 3 + int((math.sin(pulse * 6.0) + 1.0) * 0.5)
        border = SUCCESS

    draw_panel(surface, rect, theme, fill=fill, border=border, radius=14, width=width)
    inner = rect.inflate(-18, -16)
    pygame.draw.rect(surface, (13, 18, 27), inner, border_radius=10)
    pygame.draw.rect(surface, color, inner, 2, border_radius=10)
    draw_destination_icon(surface, name, (rect.centerx, rect.top + 50), color, 0.72)
    label = _render_text(fonts, name, 19 if name != "INSPECTION" else 16, theme.ink, True)
    surface.blit(label, label.get_rect(center=(rect.centerx, rect.bottom - 31)))
    dock = _render_text(fonts, "DROP ZONE", 11, theme.muted, True)
    surface.blit(dock, dock.get_rect(center=(rect.centerx, rect.bottom - 12)))
