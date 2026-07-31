from __future__ import annotations

from core.vector import Vec2
from entities.item import Item
from entities.player import PlayerInteractor
from interactables.conveyor import LinearConveyor
from managers.interaction_manager import PlayerInteractionManager
from managers.item_tracking_manager import ItemTrackingManager


class GameWorld:
    """Thin composition root for domain services used by the Pygame loop."""

    def __init__(self) -> None:
        self.items = ItemTrackingManager()
        self.interactions = PlayerInteractionManager(self.items)
        self.conveyors: dict[str, LinearConveyor] = {}

    def add_conveyor(self, conveyor: LinearConveyor) -> None:
        self.conveyors[conveyor.conveyor_id] = conveyor

    def add_player(self, player: PlayerInteractor) -> None:
        self.interactions.register_player(player)

    def spawn_on_conveyor(self, item: Item, conveyor_id: str, now: float) -> None:
        conveyor = self.conveyors[conveyor_id]
        self.items.register(item, now)
        conveyor.attach(self.items, item.entity_id, now, smooth=False)

    def update(self, dt: float, now: float) -> list[int]:
        self.interactions.update(now)
        missed: list[int] = []
        for conveyor in self.conveyors.values():
            missed.extend(conveyor.update(self.items, dt, now))
        return missed
