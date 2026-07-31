from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Mapping

from .constants import ATTRIBUTE_VALUES, DESTINATIONS, PACKAGE_SIZE


class ScreenState(Enum):
    MENU = auto()
    TUTORIAL = auto()
    BRIEFING = auto()
    PLAYING = auto()
    PAUSED = auto()
    CONTRACT_REPORT = auto()
    CAMPAIGN_REPORT = auto()
    SETTINGS = auto()


class ParcelState(Enum):
    ON_BELT = auto()
    DRAGGING = auto()
    TRACKING_SUSPENDED = auto()
    RETURNING = auto()
    SORTED = auto()
    MISSED = auto()


class InputMode(Enum):
    MOUSE = "Mouse"
    WEBCAM = "Webcam"


@dataclass(frozen=True, slots=True)
class ParcelAttributes:
    color: str
    weight: str
    mark: str
    status: str

    def value_for(self, rule_type: str) -> str:
        key = rule_type.lower()
        if not hasattr(self, key):
            raise ValueError(f"Unsupported rule type: {rule_type}")
        return str(getattr(self, key))


@dataclass(slots=True)
class Parcel:
    parcel_id: int
    attributes: ParcelAttributes
    x: float
    y: float
    speed: float
    state: ParcelState = ParcelState.ON_BELT
    width: int = PACKAGE_SIZE[0]
    height: int = PACKAGE_SIZE[1]
    drag_offset_x: float = 0.0
    drag_offset_y: float = 0.0
    return_target_y: float | None = None
    previous_x: float = 0.0
    previous_y: float = 0.0

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

    def contains(self, point: tuple[float, float]) -> bool:
        px, py = point
        return self.left <= px <= self.right and self.top <= py <= self.bottom

    def active_value(self, rule_type: str) -> str:
        return self.attributes.value_for(rule_type)

    def begin_drag(self, point: tuple[float, float]) -> None:
        self.state = ParcelState.DRAGGING
        self.drag_offset_x = point[0] - self.x
        self.drag_offset_y = point[1] - self.y

    def drag_to(self, point: tuple[float, float], bounds: tuple[int, int]) -> None:
        self.previous_x, self.previous_y = self.x, self.y
        max_x = max(0, bounds[0] - self.width)
        max_y = max(0, bounds[1] - self.height)
        self.x = min(max(point[0] - self.drag_offset_x, 0), max_x)
        self.y = min(max(point[1] - self.drag_offset_y, 0), max_y)

    def suspend_tracking(self) -> None:
        if self.state == ParcelState.DRAGGING:
            self.state = ParcelState.TRACKING_SUSPENDED

    def resume_tracking(self) -> None:
        if self.state == ParcelState.TRACKING_SUSPENDED:
            self.state = ParcelState.DRAGGING

    def reattach(self, belt_y: float) -> None:
        self.state = ParcelState.RETURNING
        self.return_target_y = belt_y - self.height / 2

    def update(self, dt: float, screen_width: int) -> bool:
        """Update motion. Returns True when the parcel is newly missed."""
        if self.state == ParcelState.ON_BELT:
            self.x += self.speed * dt
            if self.x > screen_width:
                self.state = ParcelState.MISSED
                return True
        elif self.state == ParcelState.RETURNING:
            target_y = self.return_target_y if self.return_target_y is not None else self.y
            self.y += (target_y - self.y) * min(1.0, dt * 9.0)
            if abs(target_y - self.y) < 1.5:
                self.y = target_y
                self.state = ParcelState.ON_BELT
        return False


@dataclass(slots=True)
class ContractStats:
    correct: int = 0
    wrong: int = 0
    missed: int = 0
    score: int = 0
    combo: int = 0
    best_combo: int = 0

    @property
    def resolved(self) -> int:
        return self.correct + self.wrong + self.missed

    @property
    def attempted(self) -> int:
        return self.correct + self.wrong

    @property
    def accuracy(self) -> float:
        denominator = self.resolved
        return self.correct / denominator if denominator else 0.0

    def record_correct(self) -> int:
        self.correct += 1
        self.combo += 1
        self.best_combo = max(self.best_combo, self.combo)
        points = 100 + min(200, (self.combo - 1) * 20)
        self.score += points
        return points

    def record_wrong(self) -> int:
        self.wrong += 1
        self.combo = 0
        self.score = max(0, self.score - 35)
        return -35

    def record_missed(self) -> int:
        self.missed += 1
        self.combo = 0
        self.score = max(0, self.score - 20)
        return -20


@dataclass(slots=True)
class CampaignStats:
    contract_results: list[ContractStats] = field(default_factory=list)

    @property
    def total_score(self) -> int:
        return sum(item.score for item in self.contract_results)

    @property
    def correct(self) -> int:
        return sum(item.correct for item in self.contract_results)

    @property
    def wrong(self) -> int:
        return sum(item.wrong for item in self.contract_results)

    @property
    def missed(self) -> int:
        return sum(item.missed for item in self.contract_results)

    @property
    def total(self) -> int:
        return self.correct + self.wrong + self.missed

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    @property
    def best_combo(self) -> int:
        return max((item.best_combo for item in self.contract_results), default=0)

    @property
    def grade(self) -> str:
        accuracy = self.accuracy
        if accuracy >= 0.95:
            return "S"
        if accuracy >= 0.88:
            return "A"
        if accuracy >= 0.78:
            return "B"
        if accuracy >= 0.65:
            return "C"
        return "D"


def build_mapping(rule_type: str, rng: random.Random) -> dict[str, str]:
    values = list(ATTRIBUTE_VALUES[rule_type])
    destinations = list(DESTINATIONS)
    rng.shuffle(destinations)
    return dict(zip(values, destinations, strict=True))


def make_parcel_attributes(rng: random.Random) -> ParcelAttributes:
    return ParcelAttributes(
        color=rng.choice(ATTRIBUTE_VALUES["COLOR"]),
        weight=rng.choice(ATTRIBUTE_VALUES["WEIGHT"]),
        mark=rng.choice(ATTRIBUTE_VALUES["MARK"]),
        status=rng.choice(ATTRIBUTE_VALUES["STATUS"]),
    )


def destination_for(
    attributes: ParcelAttributes,
    rule_type: str,
    mapping: Mapping[str, str],
) -> str:
    return mapping[attributes.value_for(rule_type)]
