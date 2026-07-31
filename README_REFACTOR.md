# Cargo Panic OOP Refactor

This package extracts item ownership, conveyor movement, hand/mouse interaction, and persistent tracking from the previous monolithic `main.py`.

## Bug fixed

The old loop directly set `package.position.y = BELT_Y` when a hand timed out and when a drop missed a bay. That destroyed the item's world position and made the conveyor implicitly reclaim ownership.

The new flow is:

1. `PlayerInteractionManager.grab_nearest()` detaches the item from every conveyor.
2. `ItemTrackingManager.grab()` records a `GRABBED` event and a complete immutable snapshot.
3. While held, only the interaction manager updates the position.
4. Brief camera loss moves the item to `TRACKING_SUSPENDED`; its exact position and holder are retained.
5. Recovery resumes the same item. A long timeout drops it at its last position.
6. Invalid manual drops use `REATTACHING`; the conveyor eases the item back instead of snapping it to the belt center.

## Integration with the current Pygame loop

- Keep drawing functions in `presentation/pygame/`.
- Replace `packages: list[Package]` with `world.items.active_items()`.
- Replace direct `package.position` and `package.held_by` assignments with manager calls.
- Convert domain vectors to Pygame with `pygame.Vector2(item.position.x, item.position.y)` only at the rendering boundary.
- Move `tracking.py` to `infrastructure/vision/tracking_worker.py`; its packet format is consumed by `packet_adapter.py`.

## Run tests

```bash
python -m unittest discover -s tests -v
```
