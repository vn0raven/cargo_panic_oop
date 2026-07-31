from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FeedbackEvent:
    text: str
    position: tuple[float, float]
    color: tuple[int, int, int]
    importance: int = 1
