from __future__ import annotations

from dataclasses import dataclass
import random

from core.config import PHASES
from interactables.shipping_container import ShippingContainer


@dataclass(slots=True)
class DifficultyManager:
    rng: random.Random
    next_closure_at: float = 0.0
    next_surge_at: float = 0.0
    closure_target: ShippingContainer | None = None
    closure_warning_started: bool = False
    surge_until: float = 0.0

    def reset(self, now: float) -> None:
        self.next_closure_at = now + 9.0
        self.next_surge_at = now + 12.0
        self.closure_target = None
        self.closure_warning_started = False
        self.surge_until = 0.0

    def update(
        self,
        now: float,
        phase_index: int,
        containers: list[ShippingContainer],
    ) -> tuple[float, str | None]:
        spec = PHASES[phase_index]
        message: str | None = None

        if spec.closure_enabled:
            if not self.closure_warning_started and now >= self.next_closure_at:
                available = [container for container in containers if not container.is_closed(now)]
                if available:
                    self.closure_target = self.rng.choice(available)
                    self.closure_target.warning_until = now + 2.5
                    self.closure_warning_started = True
                    message = f"{self.closure_target.destination.value} bay closing"
            elif self.closure_warning_started and self.closure_target and now >= self.closure_target.warning_until:
                self.closure_target.closed_until = now + self.rng.uniform(4.5, 6.0)
                message = f"{self.closure_target.destination.value} bay offline"
                self.next_closure_at = self.closure_target.closed_until + self.rng.uniform(7.0, 10.0)
                self.closure_target = None
                self.closure_warning_started = False

        multiplier = 1.0
        if spec.surge_enabled:
            if now >= self.next_surge_at and now >= self.surge_until:
                self.surge_until = now + 4.0
                self.next_surge_at = self.surge_until + self.rng.uniform(9.0, 13.0)
                message = "Conveyor surge"
            if now < self.surge_until:
                multiplier = 1.34

        return multiplier, message
