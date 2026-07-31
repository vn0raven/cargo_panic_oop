from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.vector import Vec2


@dataclass(slots=True)
class Entity(ABC):
    entity_id: int
    position: Vec2
    active: bool = True

    @abstractmethod
    def update(self, dt: float, now: float) -> None:
        """Advance entity-owned behavior. Managers own cross-entity behavior."""
        raise NotImplementedError
