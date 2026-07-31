from __future__ import annotations

from dataclasses import dataclass

from core.enums import HandlingTag
from entities.package import CargoPackage


@dataclass(slots=True)
class ScoreManager:
    score: int = 0
    combo: int = 0
    highest_combo: int = 0

    @property
    def multiplier(self) -> float:
        if self.combo >= 20:
            return 3.0
        if self.combo >= 10:
            return 2.0
        if self.combo >= 5:
            return 1.5
        return 1.0

    def award_delivery(self, package: CargoPackage, now: float, fragile_clean: bool) -> tuple[int, list[str]]:
        base = 100
        labels: list[str] = []
        if package.tag is HandlingTag.EXPRESS:
            base += 50
            labels.append("EXPRESS +50")
        elif package.tag is HandlingTag.DAMAGED:
            base += 75
            labels.append("SCANNED +75")

        age = package.age(now)
        speed_bonus = max(0, round(50 * (1.0 - min(age, 8.0) / 8.0)))
        if speed_bonus:
            base += speed_bonus
            labels.append(f"SPEED +{speed_bonus}")

        if package.tag is HandlingTag.FRAGILE and fragile_clean:
            base += 50
            labels.append("FRAGILE +50")

        self.combo += 1
        self.highest_combo = max(self.highest_combo, self.combo)
        gained = round(base * self.multiplier)
        self.score += gained
        return gained, labels

    def wrong_delivery(self) -> None:
        self.combo = 0
        self.score = max(0, self.score - 100)

    def miss(self) -> None:
        if self.combo >= 20:
            self.combo = 10
        elif self.combo >= 10:
            self.combo = 5
        elif self.combo >= 5:
            self.combo = 0
        else:
            self.combo = max(0, self.combo - 1)
        self.score = max(0, self.score - 75)

    def fragile_penalty(self) -> None:
        self.score = max(0, self.score - 50)
