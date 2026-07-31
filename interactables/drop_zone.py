from __future__ import annotations

from dataclasses import dataclass

from core.vector import Vec2


@dataclass(frozen=True, slots=True)
class DropZone:
    zone_id: str
    destination: str
    left: float
    top: float
    right: float
    bottom: float

    @property
    def center(self) -> Vec2:
        return Vec2((self.left + self.right) / 2.0, (self.top + self.bottom) / 2.0)

    def contains(self, point: Vec2) -> bool:
        return self.left <= point.x <= self.right and self.top <= point.y <= self.bottom
