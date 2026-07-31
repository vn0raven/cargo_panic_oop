"""Cargo Panic game package."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game import CargoPanicGame as CargoPanicGame

__all__ = ["CargoPanicGame"]


def __getattr__(name: str):
    if name == "CargoPanicGame":
        from .game import CargoPanicGame

        return CargoPanicGame
    raise AttributeError(name)
