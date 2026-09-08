from __future__ import annotations

import json
import threading
from pathlib import Path

from pydantic import BaseModel, model_validator

from .recursive_discovery import RecursiveDiscoveryState, state_digest
from .storage import DurableStore


class OmegaStateEnvelope(BaseModel):
    schema: str = "ws-omega-persisted-state-1"
    state: RecursiveDiscoveryState
    state_digest: str

    @model_validator(mode="after")
    def verify_state_digest(self) -> "OmegaStateEnvelope":
        actual = state_digest(self.state)
        if self.state_digest != actual:
            raise ValueError("persisted WS-OMEGA state digest mismatch")
        return self


class OmegaStateStore:
    """Atomic local custody for the resumable WS-OMEGA frontier.

    The state snapshot is chained through `prior_state_digest`; SARA's audit
    log records cycle-transition digests separately. This store does not run
    collectors, promote claims, or execute external actions.
    """

    def __init__(self, durable_store: DurableStore) -> None:
        self._durable = durable_store
        self.root: Path = durable_store.root
        self.path = self.root / "omega_state.json"
        self._lock = threading.RLock()
        if self.path.exists():
            DurableStore._secure_mode(self.path, 0o600, "WS-OMEGA state file")

    def load(self) -> RecursiveDiscoveryState | None:
        with self._lock:
            try:
                self.path.lstat()
            except FileNotFoundError:
                return None
            descriptor = DurableStore._open_read_descriptor(
                self.path, "WS-OMEGA state file"
            )
            with __import__("os").fdopen(descriptor, "r", encoding="utf-8") as handle:
                try:
                    payload = json.load(handle)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        "WS-OMEGA state corruption detected: invalid JSON"
                    ) from exc
            try:
                envelope = OmegaStateEnvelope.model_validate(payload)
            except ValueError as exc:
                raise RuntimeError(
                    "WS-OMEGA state corruption detected: invalid envelope"
                ) from exc
            return envelope.state

    def initialize(self, state: RecursiveDiscoveryState) -> RecursiveDiscoveryState:
        with self._lock:
            current = self.load()
            if current is not None:
                if state_digest(current) == state_digest(state):
                    return current
                raise ValueError("WS-OMEGA state is already initialized")
            self._write(state)
            return state

    def replace(
        self,
        *,
        expected_state_digest: str,
        next_state: RecursiveDiscoveryState,
    ) -> RecursiveDiscoveryState:
        with self._lock:
            current = self.load()
            if current is None:
                raise ValueError("WS-OMEGA state is not initialized")
            current_digest = state_digest(current)
            if current_digest != expected_state_digest:
                raise ValueError("WS-OMEGA state changed during cycle execution")
            if next_state.prior_state_digest != current_digest:
                raise ValueError("WS-OMEGA next state does not chain from current state")
            if next_state.cycle_index != current.cycle_index + 1:
                raise ValueError("WS-OMEGA cycle index must advance exactly once")
            self._write(next_state)
            return next_state

    def _write(self, state: RecursiveDiscoveryState) -> None:
        envelope = OmegaStateEnvelope(
            state=state,
            state_digest=state_digest(state),
        )
        self._durable._atomic_write_json(
            self.path,
            envelope.model_dump(mode="json"),
        )
        DurableStore._secure_mode(self.path, 0o600, "WS-OMEGA state file")

    def status(self) -> dict[str, object]:
        state = self.load()
        if state is None:
            return {
                "configured": True,
                "initialized": False,
                "state_file": self.path.name,
                "global_depth_limit": None,
                "physical_infinity_claimed": False,
                "claim_promotion_allowed": False,
                "external_execution_allowed": False,
            }
        nodes = [*state.frontier, *state.backlog]
        return {
            "configured": True,
            "initialized": True,
            "state_file": self.path.name,
            "cycle_index": state.cycle_index,
            "state_digest": state_digest(state),
            "frontier_count": len(state.frontier),
            "backlog_count": len(state.backlog),
            "proposal_backlog_count": len(state.proposal_backlog),
            "explored_count": len(state.explored_node_ids),
            "deepest_live_depth": max((node.depth for node in nodes), default=0),
            "global_depth_limit": None,
            "physical_infinity_claimed": False,
            "claim_promotion_allowed": False,
            "external_execution_allowed": False,
        }

    def check_storage(self) -> tuple[bool, str]:
        try:
            DurableStore._secure_mode(self.root, 0o700, "WS-OMEGA data directory")
            if self.path.exists():
                DurableStore._secure_mode(
                    self.path, 0o600, "WS-OMEGA state file"
                )
                self.load()
        except (OSError, RuntimeError, ValueError) as exc:
            return False, str(exc)
        return True, "WS-OMEGA state custody is readable and secured"
