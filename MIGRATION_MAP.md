# Original-to-demo migration map

This build retains the original repository's package-oriented OOP layout while replacing the single-rule contract flow with a unified destination-routing shift.

| Original area | Demo counterpart | Design change |
|---|---|---|
| `application/game_world.py` and main loop | `application/game.py` | Full title, play, pause, emergency, and results state machine. |
| `entities/item.py` | `entities/package.py` | Destination, body type, handling tag, urgency, scanning, and drag metrics. |
| `entities/player.py` | `entities/player.py` | Accuracy, mistakes, and average-sort-time tracking. |
| `interactables/conveyor.py` | `interactables/conveyor.py` | Variable speed, body-specific movement, surge multiplier, and miss zone. |
| `interactables/drop_zone.py` | `interactables/shipping_container.py` | Three readable destination bays with closure warnings and rejection state. |
| Tracking/interaction managers | Mouse interaction in `application/game.py` | Reliable baseline input; webcam boundary documented separately. |
| Contract/level rules | `core/config.py` phase specifications | Five continuous phases that add pressure without changing the core destination rule. |
| Existing score/report flow | `managers/score_manager.py` and shift report | Combo tiers, urgency bonuses, rank, high score, and mistake diagnosis. |

The modular boundaries are intentionally kept small so the original webcam adapter can be reintroduced later without changing the cargo domain model.
