# Cargo Panic: Night Shift — Demo Design

## Player fantasy

The player is the final sorter on an overloaded warehouse night shift. The interface begins legible and controlled, then moves through confident rhythm, prioritization pressure, controlled malfunction, and a final rush.

## Core loop

1. A package enters the conveyor.
2. The player reads the destination and handling tag.
3. The player chooses whether to sort, prioritize, or scan it.
4. The player drags it into a shipping bay.
5. Immediate score, combo, sound, and visual feedback confirms the outcome.
6. The next decision arrives faster.

## Phase pacing

| Phase | Purpose | New pressure |
|---|---|---|
| Training Shift | Teach destination matching. | Slow belt and standard cargo. |
| Normal Operations | Establish rhythm. | Heavy packages and express priority. |
| Handling Requirements | Force triage decisions. | Fragile, refrigerated, and damaged cargo. |
| System Malfunction | Disrupt learned routines. | Bay closures, shuffled bay order, and belt surges. |
| Final Rush | Test mastery. | Maximum active cargo and fastest spawn rate. |

## Readability rules

Every destination uses a name, a color, and a symbol. Color is never the only signal.

- Northport: triangle
- Eastvale: circle
- Westhaven: square

Handling tags are independent of destination. This produces combinations such as a heavy refrigerated Northport crate or a small damaged Westhaven mailer without requiring additional permanent bays.

## Scoring priorities

Accuracy is primary. Speed is a bonus. Correct deliveries build combo tiers at 5, 10, and 20 consecutive packages. A wrong bay resets the combo, while a missed package drops it by one tier.

## Demo completion target

A new player should understand the interaction within 20 seconds, finish a run in about five minutes, experience at least one recoverable crisis, and understand how to improve on a retry.
