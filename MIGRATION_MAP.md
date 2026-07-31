# Migration Map from the Existing Monolith

| Existing responsibility | New location |
|---|---|
| `Package` data and item state | `entities/item.py` |
| `HandController.held_package_id` ownership | `entities/player.py` + `managers/interaction_manager.py` |
| `nearest_package`, `package_by_id` | `managers/item_tracking_manager.py` |
| `grab_package`, `release_package` | `managers/interaction_manager.py` |
| belt movement and missed-edge detection | `interactables/conveyor.py` |
| webcam packet translation | `infrastructure/vision/packet_adapter.py` |
| MediaPipe worker | `infrastructure/vision/tracking_worker.py` |
| level/campaign rules | keep under `application/` as separate managers |
| Pygame drawing helpers | move under `presentation/pygame/` |

The item tracker is authoritative. Rendering, input, conveyors, and scoring may read snapshots or request transitions, but must not directly assign `state`, `holder_id`, `conveyor_id`, or `position`.
