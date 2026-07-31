from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from core.vector import Vec2
from managers.interaction_manager import PlayerInteractionManager


class HandTrackingPacketAdapter:
    """Maps MediaPipe worker packets into PlayerInteractionManager calls."""

    def __init__(
        self,
        interactions: PlayerInteractionManager,
        screen_width: float,
        screen_height: float,
        tracking_timeout: float,
    ) -> None:
        self._interactions = interactions
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._tracking_timeout = tracking_timeout
        self._last_seen: dict[str, float] = {}

    def apply(self, packet: dict[str, Any], now: float) -> dict[str, str]:
        states: dict[str, str] = {}
        present: set[str] = set()
        for hand in packet.get("hands", []):
            player_id = str(hand["id"])
            palm = hand["palm"]
            position = Vec2(
                min(max(float(palm[0]) * self._screen_width, 0.0), self._screen_width),
                min(max(float(palm[1]) * self._screen_height, 0.0), self._screen_height),
            )
            player = self._interactions.get_player(player_id)
            if not player.tracked:
                self._interactions.tracking_recovered(player_id, position, now)
            else:
                self._interactions.update_pointer(player_id, position, now)
            self._last_seen[player_id] = now
            present.add(player_id)
            states[player_id] = str(hand.get("state", "neutral"))

        for player_id, last_seen in tuple(self._last_seen.items()):
            if player_id not in present and now - last_seen > self._tracking_timeout:
                self._interactions.tracking_lost(player_id, now)
        return states
