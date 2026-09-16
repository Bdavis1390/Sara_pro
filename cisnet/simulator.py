from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .model import FaultWindow, LinkState, LinkType, TransferState
from .policy import PrimeSentinelPolicy
from .provenance import EchoLedger


@dataclass
class SimulationResult:
    payload_bytes: int
    received_bytes: int
    dropped_bytes: int
    completed: bool
    completed_at_s: Optional[int]
    route_changes: int
    failovers: int
    node_restarts: int
    max_relay_buffer_bytes: int
    ledger_valid: bool
    audit_events: int
    link_bytes: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "payload_bytes": self.payload_bytes,
            "received_bytes": self.received_bytes,
            "dropped_bytes": self.dropped_bytes,
            "completed": self.completed,
            "completed_at_s": self.completed_at_s,
            "route_changes": self.route_changes,
            "failovers": self.failovers,
            "node_restarts": self.node_restarts,
            "max_relay_buffer_bytes": self.max_relay_buffer_bytes,
            "ledger_valid": self.ledger_valid,
            "audit_events": self.audit_events,
            "link_bytes": self.link_bytes,
        }


class CisnetSimulation:
    """Three-node Earthward DTN-style capacity simulator.

    A (lunar asset) -> B (relay) -> C (Earth ground station)

    The model works at aggregate byte-flow level, not packet or physical layer.
    The relay buffer provides store-and-forward behavior. Link choice is made
    independently on A-B and B-C each second through PrimeSentinelPolicy.
    """

    def __init__(self, payload_bytes: int, links: Iterable[LinkState], faults: Iterable[FaultWindow] = (), policy: Optional[PrimeSentinelPolicy] = None, dt_s: int = 1) -> None:
        if payload_bytes <= 0:
            raise ValueError("payload_bytes must be positive")
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")
        self.links: Dict[str, LinkState] = {link.name: link for link in links}
        self.base = {name: (link.rate_mbps, link.survival_probability, link.up) for name, link in self.links.items()}
        self.faults = list(faults)
        self.policy = policy or PrimeSentinelPolicy()
        self.dt_s = dt_s
        self.state = TransferState(payload_bytes=payload_bytes, source_remaining=float(payload_bytes))
        self.ledger = EchoLedger()
        self._restart_active_last_step: Dict[str, bool] = {}
        self.ledger.append(0, "simulation_start", payload_bytes=payload_bytes, dt_s=dt_s)

    def _reset_links(self) -> None:
        for name, link in self.links.items():
            rate, survival, up = self.base[name]
            link.rate_mbps = rate
            link.survival_probability = survival
            link.up = up

    def _apply_faults(self, t_s: int) -> Dict[str, bool]:
        self._reset_links()
        node_down: Dict[str, bool] = {}
        for fault in self.faults:
            if not fault.active(t_s):
                continue
            if fault.node_name:
                node_down[fault.node_name] = True
            if fault.link_name and fault.link_name in self.links:
                link = self.links[fault.link_name]
                if fault.force_down:
                    link.up = False
                if fault.rate_multiplier is not None:
                    link.rate_mbps *= fault.rate_multiplier
                if fault.survival_probability is not None:
                    link.survival_probability = fault.survival_probability
        return node_down

    def _record_restart_edges(self, t_s: int, node_down: Dict[str, bool]) -> None:
        for node in {fault.node_name for fault in self.faults if fault.node_name}:
            if node is None:
                continue
            current = bool(node_down.get(node, False))
            previous = self._restart_active_last_step.get(node, False)
            if current and not previous:
                self.state.node_restarts += 1
                self.ledger.append(t_s, "node_restart_begin", node=node)
            if previous and not current:
                self.ledger.append(t_s, "node_restart_end", node=node)
            self._restart_active_last_step[node] = current

    def _leg_links(self, src: str, dst: str) -> List[LinkState]:
        return [link for link in self.links.values() if link.src == src and link.dst == dst]

    def _select_leg(self, t_s: int, src: str, dst: str, previous_name: Optional[str]) -> Optional[LinkState]:
        links = self._leg_links(src, dst)
        selected = self.policy.select(links)
        if selected is None:
            if previous_name is not None:
                self.state.route_changes += 1
                self.ledger.append(t_s, "route_unavailable", src=src, dst=dst, previous=previous_name)
            return None
        decision = self.policy.authorize(selected)
        if not decision.allowed:
            raise RuntimeError("policy.select returned unauthorized link")
        if selected.name != previous_name:
            self.state.route_changes += 1
            if previous_name is not None:
                self.state.failovers += 1
            self.ledger.append(t_s, "route_authorized", src=src, dst=dst, previous=previous_name, selected=selected.name, link_type=selected.link_type.value, rate_mbps=selected.rate_mbps, survival_probability=selected.survival_probability, policy_reason=decision.reason)
        return selected

    def run(self, max_time_s: int = 20_000) -> SimulationResult:
        if max_time_s <= 0:
            raise ValueError("max_time_s must be positive")
        for t_s in range(0, max_time_s, self.dt_s):
            node_down = self._apply_faults(t_s)
            self._record_restart_edges(t_s, node_down)
            ab = None if node_down.get("A") or node_down.get("B") else self._select_leg(t_s, "A", "B", self.state.last_ab_link)
            bc = None if node_down.get("B") or node_down.get("C") else self._select_leg(t_s, "B", "C", self.state.last_bc_link)
            self.state.last_ab_link = ab.name if ab else None
            self.state.last_bc_link = bc.name if bc else None
            if bc and self.state.relay_buffer > 0:
                capacity = bc.capacity_bytes_per_second * self.dt_s
                forwarded = min(capacity, self.state.relay_buffer)
                self.state.relay_buffer -= forwarded
                self.state.destination_received += forwarded
                self.state.link_bytes[bc.name] = self.state.link_bytes.get(bc.name, 0.0) + forwarded
            if ab and self.state.source_remaining > 0:
                capacity = ab.capacity_bytes_per_second * self.dt_s
                moved = min(capacity, self.state.source_remaining)
                self.state.source_remaining -= moved
                self.state.relay_buffer += moved
                self.state.link_bytes[ab.name] = self.state.link_bytes.get(ab.name, 0.0) + moved
            self.state.max_relay_buffer = max(self.state.max_relay_buffer, self.state.relay_buffer)
            if self.state.destination_received >= self.state.payload_bytes - 0.5:
                self.state.destination_received = float(self.state.payload_bytes)
                self.state.completed_at_s = t_s + self.dt_s
                self.ledger.append(self.state.completed_at_s, "transfer_complete", received_bytes=self.state.payload_bytes, dropped_bytes=int(round(self.state.dropped_bytes)))
                break
        completed = self.state.completed_at_s is not None
        if not completed:
            self.ledger.append(max_time_s, "simulation_timeout", received_bytes=int(self.state.destination_received))
        return SimulationResult(payload_bytes=self.state.payload_bytes, received_bytes=int(round(self.state.destination_received)), dropped_bytes=int(round(self.state.dropped_bytes)), completed=completed, completed_at_s=self.state.completed_at_s, route_changes=self.state.route_changes, failovers=self.state.failovers, node_restarts=self.state.node_restarts, max_relay_buffer_bytes=int(round(self.state.max_relay_buffer)), ledger_valid=self.ledger.verify(), audit_events=len(self.ledger.events), link_bytes={name: int(round(value)) for name, value in self.state.link_bytes.items()})


def build_reference_simulation(payload_bytes: int = 100_000_000_000) -> CisnetSimulation:
    """Construct CISNET-DEMO-01 reference scenario.

    Rates are benchmark-style engineering inputs, not claims that Worldshepherd
    hardware has demonstrated these rates.
    """
    links = [
        LinkState("ab_optical", "A", "B", LinkType.OPTICAL, rate_mbps=622.0, survival_probability=0.97),
        LinkState("ab_rf", "A", "B", LinkType.RF, rate_mbps=80.0, survival_probability=0.995),
        LinkState("bc_optical", "B", "C", LinkType.OPTICAL, rate_mbps=622.0, survival_probability=0.97),
        LinkState("bc_rf", "B", "C", LinkType.RF, rate_mbps=100.0, survival_probability=0.995),
    ]
    faults = [
        FaultWindow(180, 300, link_name="bc_optical", force_down=True, reason="cloud_outage"),
        FaultWindow(420, 510, link_name="ab_optical", force_down=True, reason="pointing_loss"),
        FaultWindow(700, 790, link_name="bc_optical", rate_multiplier=0.15, survival_probability=0.35, reason="degradation"),
        FaultWindow(900, 910, node_name="B", reason="relay_restart"),
        FaultWindow(1100, 1200, link_name="bc_rf", rate_multiplier=0.20, reason="rf_congestion"),
        FaultWindow(1250, 1340, link_name="bc_optical", force_down=True, reason="weather_outage"),
    ]
    return CisnetSimulation(payload_bytes=payload_bytes, links=links, faults=faults)
