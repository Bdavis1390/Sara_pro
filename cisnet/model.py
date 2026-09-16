from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class LinkType(str, Enum):
    OPTICAL = "optical"
    RF = "rf"


@dataclass
class LinkState:
    name: str
    src: str
    dst: str
    link_type: LinkType
    rate_mbps: float
    survival_probability: float = 1.0
    up: bool = True
    trusted: bool = True

    @property
    def capacity_bytes_per_second(self) -> float:
        return self.rate_mbps * 1_000_000 / 8.0


@dataclass
class FaultWindow:
    start_s: int
    end_s: int
    link_name: Optional[str] = None
    node_name: Optional[str] = None
    rate_multiplier: Optional[float] = None
    survival_probability: Optional[float] = None
    force_down: bool = False
    reason: str = "fault"

    def active(self, t_s: int) -> bool:
        return self.start_s <= t_s < self.end_s


@dataclass
class TransferState:
    payload_bytes: int
    source_remaining: float
    relay_buffer: float = 0.0
    destination_received: float = 0.0
    dropped_bytes: float = 0.0
    route_changes: int = 0
    failovers: int = 0
    node_restarts: int = 0
    last_ab_link: Optional[str] = None
    last_bc_link: Optional[str] = None
    completed_at_s: Optional[int] = None
    max_relay_buffer: float = 0.0
    link_bytes: Dict[str, float] = field(default_factory=dict)
