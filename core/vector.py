from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(slots=True)
class Vec2:
    """Engine-independent 2D vector used by the domain layer."""

    x: float
    y: float

    def copy(self) -> "Vec2":
        return Vec2(self.x, self.y)

    def distance_squared_to(self, other: "Vec2") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy

    def distance_to(self, other: "Vec2") -> float:
        return math.sqrt(self.distance_squared_to(other))

    def lerp(self, target: "Vec2", amount: float) -> "Vec2":
        amount = max(0.0, min(1.0, amount))
        return Vec2(
            self.x + (target.x - self.x) * amount,
            self.y + (target.y - self.y) * amount,
        )

    def almost_equal(self, other: "Vec2", tolerance: float = 1e-6) -> bool:
        return abs(self.x - other.x) <= tolerance and abs(self.y - other.y) <= tolerance
