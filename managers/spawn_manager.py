from __future__ import annotations

from dataclasses import dataclass, field
import random

from pygame.math import Vector2

from core.config import PHASES
from core.enums import Destination, HandlingTag, PackageKind
from entities.package import CargoPackage


@dataclass(slots=True)
class SpawnManager:
    rng: random.Random
    next_package_id: int = 1
    next_spawn_at: float = 0.0
    recent_destinations: list[Destination] = field(default_factory=list)

    def reset(self, now: float) -> None:
        self.next_package_id = 1
        self.next_spawn_at = now + 1.0
        self.recent_destinations.clear()

    def can_spawn(self, now: float, active_count: int, phase_index: int) -> bool:
        spec = PHASES[phase_index]
        return now >= self.next_spawn_at and active_count < spec.max_active

    def schedule_next(self, now: float, phase_index: int) -> None:
        spec = PHASES[phase_index]
        jitter = self.rng.uniform(-0.16, 0.18)
        self.next_spawn_at = now + max(0.55, spec.spawn_interval + jitter)

    def _destination(self) -> Destination:
        options = list(Destination)
        if len(self.recent_destinations) >= 2 and self.recent_destinations[-1] == self.recent_destinations[-2]:
            repeated = self.recent_destinations[-1]
            options = [item for item in options if item is not repeated]
        destination = self.rng.choice(options)
        self.recent_destinations.append(destination)
        self.recent_destinations = self.recent_destinations[-3:]
        return destination

    def spawn(self, now: float, phase_index: int, belt_y: float) -> CargoPackage:
        spec = PHASES[phase_index]
        kind = PackageKind(self.rng.choice(spec.allowed_kinds))
        tag_weights = {
            "Standard": 0.50,
            "Fragile": 0.14,
            "Refrigerated": 0.13,
            "Express": 0.13,
            "Damaged": 0.10,
        }
        tags = list(spec.allowed_tags)
        weights = [tag_weights[tag] for tag in tags]
        tag = HandlingTag(self.rng.choices(tags, weights=weights, k=1)[0])

        package = CargoPackage(
            package_id=self.next_package_id,
            destination=self._destination(),
            kind=kind,
            tag=tag,
            position=Vector2(-80, belt_y),
            spawned_at=now,
            label_revealed=tag is not HandlingTag.DAMAGED,
        )
        self.next_package_id += 1
        self.schedule_next(now, phase_index)
        return package
