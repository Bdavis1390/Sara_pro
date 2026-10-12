from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class RegimeChangeDetector:
    surprise_threshold_nats: float = 2.0
    consecutive_threshold: int = 2
    recent_surprises: list[float] = field(default_factory=list)
    regime_epoch: int = 0

    def observe(self, surprise_nats: float) -> bool:
        if surprise_nats < 0:
            raise ValueError("surprise cannot be negative")
        self.recent_surprises.append(surprise_nats)
        self.recent_surprises = self.recent_surprises[-self.consecutive_threshold:]
        if (
            len(self.recent_surprises) == self.consecutive_threshold
            and all(
                value >= self.surprise_threshold_nats
                for value in self.recent_surprises
            )
        ):
            self.regime_epoch += 1
            self.recent_surprises.clear()
            return True
        return False
