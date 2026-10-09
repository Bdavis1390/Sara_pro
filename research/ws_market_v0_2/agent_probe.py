from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Any, Callable, Iterable, Protocol

from research.ws_market_v0_1.ws_market import EventLedger


class AgentProbeError(ValueError):
    """Raised when an experiment cannot be run without losing provenance."""


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise AgentProbeError(f"{path} contains a non-finite float")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise AgentProbeError(f"{path} contains a non-string object key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise AgentProbeError(
        f"{path} contains non-JSON type {type(value).__name__}"
    )


def _canonical(value: Any) -> str:
    _validate_json_value(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json_clone(value: Any) -> Any:
    """Return a detached, standards-compatible JSON value."""
    return json.loads(_canonical(value))


@dataclass(frozen=True)
class AgentDescriptor:
    agent_id: str
    provider: str
    model: str
    version: str | None = None

    def public_identity(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProbeObservation:
    observation_id: str
    market_state: dict[str, Any]
    news: tuple[dict[str, Any], ...] = ()

    def payload(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "market_state": self.market_state,
            "news": list(self.news),
        }


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    seed: int
    market_mechanism: str
    code_revision: str
    prompt_template_hash: str
    scenario_hash: str
    agents: tuple[AgentDescriptor, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "seed": self.seed,
            "market_mechanism": self.market_mechanism,
            "code_revision": self.code_revision,
            "prompt_template_hash": self.prompt_template_hash,
            "scenario_hash": self.scenario_hash,
            "agents": [
                descriptor.public_identity()
                for descriptor in sorted(self.agents, key=lambda item: item.agent_id)
            ],
        }

    def digest(self) -> str:
        return _digest(self.payload())


class BlackBoxAgent(Protocol):
    descriptor: AgentDescriptor

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Return one standards-compatible JSON object action."""


@dataclass
class FunctionAgentAdapter:
    descriptor: AgentDescriptor
    function: Callable[[dict[str, Any]], dict[str, Any]]

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        return self.function(observation)


@dataclass(frozen=True)
class AgentActionRecord:
    observation_id: str
    agent_id: str
    action: dict[str, Any]
    action_hash: str


@dataclass(frozen=True)
class ProbeRun:
    manifest_digest: str
    records: tuple[AgentActionRecord, ...]
    ledger_digest: str


def _ensure_json_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentProbeError(f"{context} must return a JSON object")
    try:
        _canonical(value)
    except (AgentProbeError, TypeError, ValueError) as exc:
        raise AgentProbeError(
            f"{context} returned a non-JSON-compatible object"
        ) from exc
    return value


def _adapter_map(
    manifest: ExperimentManifest,
    adapters: Iterable[BlackBoxAgent],
) -> dict[str, BlackBoxAgent]:
    expected = {item.agent_id: item for item in manifest.agents}
    if len(expected) != len(manifest.agents):
        raise AgentProbeError("manifest contains duplicate agent_id values")

    actual: dict[str, BlackBoxAgent] = {}
    for adapter in adapters:
        agent_id = adapter.descriptor.agent_id
        if agent_id in actual:
            raise AgentProbeError(f"duplicate adapter for agent_id {agent_id!r}")
        actual[agent_id] = adapter

    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise AgentProbeError(
            f"adapter set does not match manifest; missing={missing}, extra={extra}"
        )

    for agent_id, descriptor in expected.items():
        if actual[agent_id].descriptor != descriptor:
            raise AgentProbeError(
                f"adapter descriptor mismatch for agent_id {agent_id!r}"
            )

    return actual


def _action_event_id(observation_id: str, agent_id: str) -> str:
    return "action:" + _digest(
        {
            "observation_id": observation_id,
            "agent_id": agent_id,
        }
    )


def run_probe(
    manifest: ExperimentManifest,
    adapters: Iterable[BlackBoxAgent],
    observations: Iterable[ProbeObservation],
) -> tuple[ProbeRun, EventLedger]:
    """Run a deterministic orchestration envelope around black-box agents.

    The black-box implementation itself may be nondeterministic. This function
    does not pretend otherwise; it deterministically records the manifest,
    observation order, returned action, and action digest for later comparison.
    """

    adapter_by_id = _adapter_map(manifest, adapters)
    ledger = EventLedger()
    manifest_payload = manifest.payload()

    ledger.append(
        f"manifest:{manifest.experiment_id}",
        "experiment_manifest",
        {
            **manifest_payload,
            "manifest_digest": manifest.digest(),
        },
    )

    records: list[AgentActionRecord] = []
    seen_observations: set[str] = set()

    for observation in observations:
        if observation.observation_id in seen_observations:
            raise AgentProbeError(
                f"duplicate observation_id {observation.observation_id!r}"
            )
        seen_observations.add(observation.observation_id)

        payload = _json_clone(observation.payload())
        ledger.append(
            f"observation:{observation.observation_id}",
            "observation",
            _json_clone(payload),
        )

        for agent_id in sorted(adapter_by_id):
            adapter = adapter_by_id[agent_id]
            raw_action = adapter.act(_json_clone(payload))
            action = _json_clone(
                _ensure_json_object(
                    raw_action,
                    f"agent {agent_id!r}",
                )
            )
            action_hash = _digest(action)
            record = AgentActionRecord(
                observation_id=observation.observation_id,
                agent_id=agent_id,
                action=_json_clone(action),
                action_hash=action_hash,
            )
            records.append(record)
            ledger.append(
                _action_event_id(observation.observation_id, agent_id),
                "agent_action",
                {
                    "observation_id": observation.observation_id,
                    "agent_id": agent_id,
                    "action": _json_clone(action),
                    "action_hash": action_hash,
                },
            )

    run = ProbeRun(
        manifest_digest=manifest.digest(),
        records=tuple(records),
        ledger_digest=ledger.digest(),
    )
    return run, ledger
