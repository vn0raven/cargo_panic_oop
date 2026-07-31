from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlayerStats:
    total_sorted: int = 0
    correct_sorted: int = 0
    missed: int = 0
    wrong: int = 0
    fragile_mishandled: int = 0
    expired: int = 0
    total_sort_time: float = 0.0

    @property
    def accuracy(self) -> float:
        attempts = self.correct_sorted + self.wrong + self.missed + self.expired
        if attempts <= 0:
            return 100.0
        return 100.0 * self.correct_sorted / attempts

    @property
    def average_sort_time(self) -> float:
        if self.correct_sorted <= 0:
            return 0.0
        return self.total_sort_time / self.correct_sorted
