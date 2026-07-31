from __future__ import annotations

from dataclasses import dataclass
import math
import random

import pygame
from pygame.math import Vector2


@dataclass(slots=True)
class Particle:
    position: Vector2
    velocity: Vector2
    life: float
    max_life: float
    color: tuple[int, int, int]


@dataclass(slots=True)
class FloatingText:
    text: str
    position: Vector2
    life: float
    color: tuple[int, int, int]
    scale: float = 1.0


class FeedbackManager:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.texts: list[FloatingText] = []
        self.banner_text = ""
        self.banner_until = 0.0
        self.banner_color = (239, 243, 249)

    def reset(self) -> None:
        self.particles.clear()
        self.texts.clear()
        self.banner_text = ""
        self.banner_until = 0.0

    def burst(self, position: tuple[float, float], color: tuple[int, int, int], count: int = 22) -> None:
        origin = Vector2(position)
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            speed = random.uniform(75.0, 230.0)
            life = random.uniform(0.3, 0.7)
            self.particles.append(
                Particle(origin.copy(), Vector2(math.cos(angle), math.sin(angle)) * speed, life, life, color)
            )

    def add_text(
        self,
        text: str,
        position: tuple[float, float],
        color: tuple[int, int, int],
        scale: float = 1.0,
    ) -> None:
        self.texts.append(FloatingText(text, Vector2(position), 1.0, color, scale))

    def banner(self, text: str, color: tuple[int, int, int], now: float, duration: float = 2.0) -> None:
        self.banner_text = text
        self.banner_color = color
        self.banner_until = now + duration

    def update(self, dt: float) -> None:
        for particle in self.particles:
            particle.life -= dt
            particle.position += particle.velocity * dt
            particle.velocity *= 0.965
        self.particles = [item for item in self.particles if item.life > 0]

        for text in self.texts:
            text.life -= dt
            text.position.y -= 38.0 * dt
        self.texts = [item for item in self.texts if item.life > 0]

    def draw(self, surface: pygame.Surface, fonts: dict[str, pygame.font.Font], now: float) -> None:
        for particle in self.particles:
            radius = max(1, round(5 * particle.life / particle.max_life))
            pygame.draw.circle(surface, particle.color, particle.position, radius)

        for text in self.texts:
            font = fonts["medium"] if text.scale >= 1.2 else fonts["small"]
            rendered = font.render(text.text, True, text.color)
            surface.blit(rendered, rendered.get_rect(center=text.position))

        if self.banner_text and now < self.banner_until:
            rendered = fonts["large"].render(self.banner_text, True, self.banner_color)
            rect = rendered.get_rect(midtop=(surface.get_width() // 2, 112))
            panel = rect.inflate(36, 20)
            overlay = pygame.Surface(panel.size, pygame.SRCALPHA)
            overlay.fill((10, 14, 21, 220))
            surface.blit(overlay, panel.topleft)
            pygame.draw.rect(surface, self.banner_color, panel, 2, border_radius=10)
            surface.blit(rendered, rect)
