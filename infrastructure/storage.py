from __future__ import annotations

import json
from pathlib import Path


class HighScoreStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".cargo_panic_highscore.json"

    def load(self) -> int:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return max(0, int(data.get("high_score", 0)))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return 0

    def save_if_higher(self, score: int) -> int:
        current = self.load()
        best = max(current, int(score))
        if best != current:
            try:
                self.path.write_text(json.dumps({"high_score": best}, indent=2), encoding="utf-8")
            except OSError:
                pass
        return best
