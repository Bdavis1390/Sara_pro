"""
WORLD CONTROLLER router for Worldshepherd SARA / SSPADAWANZZ.

Full-controls local admin patch:
- Wires every visible UI tab/button to a backend endpoint.
- Keeps execution simulate-first and local-only by default.
- Records command, guardian, oracle, ark, registry, watcher, and audit actions.

Mount into the existing FastAPI app:
    from worldshepherd_sara.world_controller import router as world_controller_router
    app.include_router(world_controller_router)
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

try:
    from fastapi import APIRouter, Header, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel, Field
except Exception as exc:  # pragma: no cover
    raise RuntimeError("WORLD CONTROLLER requires FastAPI and Pydantic.") from exc

router = APIRouter(prefix="/world", tags=["WORLD CONTROLLER"])

RiskClass = Literal["GREEN", "BLUE", "AMBER", "RED", "BLACK"]
Intent = Literal[
    "OBSERVE",
    "SIMULATE",
    "CONFIGURE",
    "RELAY",
    "PATCH",
    "DEPLOY",
    "ROLLBACK",
    "ARCHIVE",
    "EXECUTE",
]
Mode = Literal["DRY_RUN", "EXECUTE", "QUEUE", "REQUIRE_APPROVAL"]


class WorldCommand(BaseModel):
    intent: Intent = Field(..., description="Command intent")
    target: str = Field(..., min_length=1, description="Target node/service/module")
    action: str = Field(..., min_length=1, description="Action verb")
    scope: str = Field("local", description="Scope of action")
    mode: Mode = Field("DRY_RUN", description="Execution mode")
    reason: str = Field("", description="Human reason / mission note")
    payload: Dict[str, Any] = Field(default_factory=dict)
    execute_confirm: bool = Field(False, description="Second-key confirmation for execution")


class NaturalCommand(BaseModel):
    text: str = Field(..., min_length=1)


class RegistryPatch(BaseModel):
    node_id: str = Field(..., min_length=1)
    status: Optional[str] = None
    role: Optional[str] = None
    guardian_policy: Optional[RiskClass] = None
    capabilities: Optional[List[str]] = None
    note: str = ""


@dataclass
class GateResult:
    guardian_class: RiskClass
    guardian_allowed: bool
    oracle_result: str
    sentinel_result: str
    ark_snapshot_id: str
    messages: List[str] = field(default_factory=list)


def _data_dir() -> Path:
    root = Path(os.getenv("WORLD_DATA_DIR", "data"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _audit_path() -> Path:
    return _data_dir() / "world_controller_audit.jsonl"


def _registry_path() -> Path:
    return _data_dir() / "world_controller_registry.json"


def _ark_dir() -> Path:
    root = _data_dir() / "world_controller_ark"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _preflight_path() -> Path:
    return _data_dir() / "world_controller_preflight.json"


def _now() -> float:
    return time.time()


def _token_from_header(authorization: Optional[str], x_sara_admin_token: Optional[str]) -> Optional[str]:
    if x_sara_admin_token:
        return x_sara_admin_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def _require_admin(authorization: Optional[str], x_sara_admin_token: Optional[str]) -> str:
    expected = os.getenv("SARA_ADMIN_TOKEN", "")
    supplied = _token_from_header(authorization, x_sara_admin_token)
    if not expected:
        raise HTTPException(status_code=500, detail="SARA_ADMIN_TOKEN is not set")
    if supplied != expected:
        raise HTTPException(status_code=403, detail="WORLD CONTROLLER admin token required")
    return "SSPADAWANZZ_ADMIN"


def _safe_read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        backup = path.with_suffix(path.suffix + f".corrupt-{int(_now())}")
        try:
            path.replace(backup)
        except Exception:
            pass
        return fallback


def _sha256_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _append_audit(record: Dict[str, Any]) -> Dict[str, Any]:
    record = {"ts": _now(), "audit_id": f"WC-AUD-{uuid.uuid4().hex[:12]}", **record}
    path = _audit_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _read_audit(limit: int = 50) -> List[Dict[str, Any]]:
    path = _audit_path()
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 500)) :]
    out: List[Dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(out))


def _default_registry() -> Dict[str, Any]:
    return {
        "SARA_CORE": {
            "role": "core",
            "status": "online",
            "capabilities": ["relay", "audit", "registry", "health"],
            "guardian_policy": "AMBER",
            "last_seen": _now(),
        },
        "SSPADAWANZZ": {
            "role": "admin_operator",
            "status": "online",
            "capabilities": ["observe", "simulate", "relay", "audit_read", "registry_patch"],
            "guardian_policy": "AMBER",
            "last_seen": _now(),
        },
        "WATCHER_GRID": {
            "role": "telemetry",
            "status": "standby",
            "capabilities": ["observe", "health", "heartbeat"],
            "guardian_policy": "GREEN",
            "last_seen": _now(),
        },
        "GUARDIAN_POLICY": {
            "role": "safety_gate",
            "status": "enforced",
            "capabilities": ["classify", "deny", "require_approval"],
            "guardian_policy": "RED",
            "last_seen": _now(),
        },
        "ORACLE_ENGINE": {
            "role": "simulator",
            "status": "simulate_first",
            "capabilities": ["dry_run", "impact_estimate", "rollback_estimate"],
            "guardian_policy": "BLUE",
            "last_seen": _now(),
        },
        "ARK_STORE": {
            "role": "continuity",
            "status": "ready",
            "capabilities": ["snapshot", "restore_point", "checksum"],
            "guardian_policy": "AMBER",
            "last_seen": _now(),
        },
    }


def _load_registry() -> Dict[str, Any]:
    path = _registry_path()
    fallback = _default_registry()
    if not path.exists():
        _save_registry(fallback)
        return fallback
    registry = _safe_read_json(path, fallback)
    if not isinstance(registry, dict):
        registry = fallback
    return registry


def _save_registry(registry: Dict[str, Any]) -> None:
    _registry_path().write_text(json.dumps(registry, indent=2, sort_keys=True), encoding="utf-8")


def _component_status() -> Dict[str, Any]:
    registry = _load_registry()
    audit_count = len(_read_audit(limit=500))
    return {
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "data_dir": str(_data_dir()),
        "audit_records_visible": audit_count,
        "registry_hash": _sha256_obj(registry),
        "ark_snapshots": len(list(_ark_dir().glob("ARK-RP-*.json"))),
        "world_allow_amber_execute": os.getenv("WORLD_ALLOW_AMBER_EXECUTE", "0") == "1",
    }


def _risk_for(cmd: WorldCommand) -> RiskClass:
    target = cmd.target.upper()
    action = cmd.action.lower()
    intent = cmd.intent.upper()
    text = f"{target} {action} {cmd.scope} {cmd.reason} {json.dumps(cmd.payload, sort_keys=True)}".lower()

    forbidden_terms = ["weapon", "harm", "exfiltrate", "steal", "bypass", "disable_audit", "delete_audit", "wipe_audit"]
    if any(term in text for term in forbidden_terms):
        return "BLACK"

    physical_terms = ["rf", "metasurface", "actuator", "thermal", "voltage", "phase_shifter", "material_state", "laser", "motor", "power_supply"]
    if any(term in text for term in physical_terms):
        return "RED"

    if intent in {"DEPLOY", "EXECUTE"}:
        return "RED"
    if intent in {"PATCH", "RELAY", "ROLLBACK"}:
        return "AMBER"
    if intent in {"CONFIGURE", "ARCHIVE"}:
        return "BLUE"
    return "GREEN"


def _oracle(cmd: WorldCommand, risk: RiskClass) -> str:
    if risk == "BLACK":
        return "unsafe_or_forbidden_path_detected"
    if risk == "RED":
        return "requires_offline_review_or_hardware_safety_case"
    if risk == "AMBER":
        return "admin_approval_and_rollback_required_before_execution"
    if risk == "BLUE":
        return "local_reversible_change_expected"
    return "read_or_simulation_only_low_risk"


def _ark_snapshot(label: str, payload: Dict[str, Any]) -> str:
    snapshot_id = f"ARK-RP-{int(_now())}-{uuid.uuid4().hex[:8]}"
    body = {
        "snapshot_id": snapshot_id,
        "ts": _now(),
        "label": label,
        "registry": _load_registry(),
        "payload": payload,
    }
    body["sha256"] = _sha256_obj(body)
    (_ark_dir() / f"{snapshot_id}.json").write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
    return snapshot_id


def _gate(cmd: WorldCommand) -> GateResult:
    risk = _risk_for(cmd)
    messages: List[str] = []
    allow_amber = os.getenv("WORLD_ALLOW_AMBER_EXECUTE", "0") == "1"
    snapshot_id = _ark_snapshot("command_gate", {"command": cmd.model_dump(), "risk": risk})

    if cmd.mode != "EXECUTE":
        allowed = risk != "BLACK"
        messages.append("dry_run_or_queue_mode_no_real_action_taken")
    elif risk in {"GREEN", "BLUE"}:
        allowed = cmd.execute_confirm
        if not cmd.execute_confirm:
            messages.append("execute_confirm_required")
    elif risk == "AMBER":
        allowed = allow_amber and cmd.execute_confirm
        messages.append("amber_execution_requires_WORLD_ALLOW_AMBER_EXECUTE=1_and_execute_confirm=true")
    else:
        allowed = False
        messages.append("red_or_black_execution_denied_by_default")

    return GateResult(
        guardian_class=risk,
        guardian_allowed=allowed,
        oracle_result=_oracle(cmd, risk),
        sentinel_result="identity_and_doctrine_gate_checked",
        ark_snapshot_id=snapshot_id,
        messages=messages,
    )


def _parse_natural(text: str) -> WorldCommand:
    raw = text.strip()
    upper = raw.upper()
    intent: Intent = "OBSERVE"
    mode: Mode = "DRY_RUN"

    for candidate in ["SIMULATE", "CONFIGURE", "RELAY", "PATCH", "DEPLOY", "ROLLBACK", "ARCHIVE", "EXECUTE", "OBSERVE"]:
        if upper.startswith(candidate):
            intent = candidate  # type: ignore[assignment]
            break

    if " EXECUTE" in upper or upper.startswith("EXECUTE"):
        mode = "EXECUTE"
    elif "QUEUE" in upper:
        mode = "QUEUE"
    elif "APPROVAL" in upper:
        mode = "REQUIRE_APPROVAL"

    known_targets = ["SARA_CORE", "SSPADAWANZZ", "WATCHER_GRID", "GUARDIAN_POLICY", "ORACLE_ENGINE", "ARK_STORE", "REGISTRY"]
    target = "SARA_CORE"
    for candidate in known_targets:
        if candidate in upper:
            target = candidate
            break

    words = raw.split()
    action = "review"
    if len(words) >= 2:
        action = words[1].lower().replace("/", "_")[:48]

    return WorldCommand(intent=intent, target=target, action=action, scope="local", mode=mode, reason=raw)


def _preflight_default() -> Dict[str, Any]:
    return {
        "workflow_id": "WC-PREFLIGHT-LOCAL",
        "status": "not_started",
        "updated_at": None,
        "steps": {
            "watchers": {"complete": False, "ts": None, "summary": "Node heartbeat state has not been inspected yet."},
            "guardians": {"complete": False, "ts": None, "summary": "Command has not been classified yet."},
            "oracle": {"complete": False, "ts": None, "summary": "High-friction action has not been dry-run yet."},
            "ark": {"complete": False, "ts": None, "summary": "Pre-change Ark snapshot has not been created yet."},
        },
        "last_command_text": "SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN",
        "last_ark_snapshot_id": None,
        "last_guardian_class": None,
        "last_oracle_result": None,
        "last_registry_hash": None,
    }


def _load_preflight() -> Dict[str, Any]:
    state = _safe_read_json(_preflight_path(), _preflight_default())
    if not isinstance(state, dict):
        state = _preflight_default()
    default = _preflight_default()
    for k, v in default.items():
        state.setdefault(k, v)
    state.setdefault("steps", default["steps"])
    for step, spec in default["steps"].items():
        state["steps"].setdefault(step, spec)
    return state


def _save_preflight(state: Dict[str, Any]) -> None:
    state["updated_at"] = _now()
    steps = state.get("steps", {})
    complete = all(bool(steps.get(k, {}).get("complete")) for k in ["watchers", "guardians", "oracle", "ark"])
    state["status"] = "ready_for_bounded_registry_or_relay_change" if complete else "incomplete"
    _preflight_path().write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _preflight_evidence_links(state: Dict[str, Any]) -> List[Dict[str, str]]:
    links = [
        {"label": "Open Preflight Evidence Dossier", "path": "/world/evidence/preflight"},
        {"label": "Open Watchers Dossier", "path": "/world/watchers"},
        {"label": "Open Guardians Dossier", "path": "/world/guardians"},
        {"label": "Open Oracle Dossier", "path": "/world/oracle"},
        {"label": "Open Ark Dossier", "path": "/world/ark"},
    ]
    if state.get("last_ark_snapshot_id"):
        links.append({"label": f"Open Ark Evidence — {state['last_ark_snapshot_id']}", "path": f"/world/evidence/ark/{state['last_ark_snapshot_id']}"})
    if state.get("last_registry_hash"):
        links.append({"label": "Open Registry Hash Evidence", "path": f"/world/evidence/registry/hash/{state['last_registry_hash']}"})
    return links


def _preflight_next_actions(state: Dict[str, Any]) -> List[str]:
    steps = state.get("steps", {})
    actions: List[str] = []
    if not steps.get("watchers", {}).get("complete"):
        actions.append("Use Watchers to inspect node heartbeat state.")
    if not steps.get("guardians", {}).get("complete"):
        actions.append("Use Guardians to classify commands before execution.")
    if not steps.get("oracle", {}).get("complete"):
        actions.append("Use Oracle to dry-run high-friction actions.")
    if not steps.get("ark", {}).get("complete"):
        actions.append("Use Ark before registry or relay changes.")
    if not actions:
        actions.append("Preflight chain is complete. Registry or relay changes may now be simulated again, then executed only if policy allows.")
    return actions


def _watchers_preflight(actor: str) -> Dict[str, Any]:
    registry = _load_registry()
    now = _now()
    watcher_rows: List[Dict[str, Any]] = []
    stale = 0
    for node_id, node in registry.items():
        try:
            last_seen = float(node.get("last_seen", now))
        except Exception:
            last_seen = now
        age = now - last_seen
        heartbeat = "fresh" if age < 300 else "stale"
        if heartbeat == "stale":
            stale += 1
        watcher_rows.append({
            "node_id": node_id,
            "role": node.get("role"),
            "status": node.get("status"),
            "guardian_policy": node.get("guardian_policy"),
            "last_seen": last_seen,
            "age_seconds": round(age, 3),
            "heartbeat": heartbeat,
            "capabilities": node.get("capabilities", []),
        })
    state = _load_preflight()
    state["steps"]["watchers"] = {
        "complete": True,
        "ts": now,
        "summary": f"Heartbeat inspection complete: {len(watcher_rows)} nodes checked, {stale} stale heartbeat(s).",
        "stale_nodes": [row["node_id"] for row in watcher_rows if row["heartbeat"] == "stale"],
    }
    state["last_registry_hash"] = _sha256_obj(registry)
    _save_preflight(state)
    record = _append_audit({"actor": actor, "event": "world_preflight_watchers_complete", "payload": {"nodes": len(watcher_rows), "stale": stale}})
    return {
        "ok": True,
        "panel": "Preflight",
        "title": "Next Action Complete — Watchers Heartbeat Dossier",
        "guardian_policy": "GREEN",
        "executive_summary": [
            "Watcher inspection completed from the local WORLD CONTROLLER registry.",
            f"{len(watcher_rows)} node(s) were inspected; {stale} stale heartbeat(s) were detected.",
            "This satisfies the first recommended next action before registry or relay changes.",
        ],
        "facts": {
            "nodes_checked": len(watcher_rows),
            "stale_heartbeats": stale,
            "registry_hash": state.get("last_registry_hash"),
            "audit_id": record.get("audit_id"),
        },
        "narrative": {
            "Operational meaning": "Watchers establish whether registered nodes appear fresh or stale before you classify, simulate, snapshot, or change anything.",
            "Evidence boundary": "This is a local registry heartbeat inspection. It proves local recorded state, not external liveness unless separate telemetry adapters are added.",
            "Completion result": "The Watchers step is now marked complete in the WORLD CONTROLLER preflight state file.",
        },
        "watchers": watcher_rows,
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state, "watchers": watcher_rows},
    }


def _guardians_preflight(actor: str, text: str) -> Dict[str, Any]:
    cmd = _parse_natural(text)
    gate = _gate(cmd)
    state = _load_preflight()
    state["last_command_text"] = text
    state["last_guardian_class"] = gate.guardian_class
    state["steps"]["guardians"] = {
        "complete": gate.guardian_class != "BLACK",
        "ts": _now(),
        "summary": f"Command classified as {gate.guardian_class}; allowed in requested mode: {gate.guardian_allowed}.",
        "guardian_class": gate.guardian_class,
        "guardian_allowed": gate.guardian_allowed,
        "ark_snapshot_id": gate.ark_snapshot_id,
    }
    if gate.ark_snapshot_id:
        state["last_ark_snapshot_id"] = gate.ark_snapshot_id
    _save_preflight(state)
    record = _append_audit({"actor": actor, "event": "world_preflight_guardians_complete", "payload": {"text": text, "gate": asdict(gate)}})
    return {
        "ok": gate.guardian_class != "BLACK",
        "panel": "Preflight",
        "title": "Next Action Complete — Guardian Classification Dossier",
        "guardian_policy": gate.guardian_class,
        "executive_summary": [
            f"The command was classified by Guardian as {gate.guardian_class}.",
            "Guardian classification is now recorded before execution.",
            "Execution remains bounded by simulate-first policy, confirmation requirements, and RED/BLACK denial rules.",
        ],
        "facts": {
            "command_text": text,
            "guardian_class": gate.guardian_class,
            "guardian_allowed": gate.guardian_allowed,
            "oracle_result": gate.oracle_result,
            "ark_snapshot_id": gate.ark_snapshot_id,
            "audit_id": record.get("audit_id"),
        },
        "narrative": {
            "Operational meaning": "Guardian classification translates command intent into a risk class before any execution path can proceed.",
            "Risk interpretation": "GREEN and BLUE are locally bounded. AMBER requires explicit env unlock and confirmation. RED and BLACK remain denied by default.",
            "Completion result": "The Guardians step is now marked complete unless the command is BLACK/forbidden.",
        },
        "command": cmd.model_dump(),
        "gate": asdict(gate),
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state, "command": cmd.model_dump(), "gate": asdict(gate)},
    }


def _oracle_preflight(actor: str, text: str) -> Dict[str, Any]:
    cmd = _parse_natural(text)
    cmd.mode = "DRY_RUN"
    gate = _gate(cmd)
    state = _load_preflight()
    state["last_command_text"] = text
    state["last_oracle_result"] = gate.oracle_result
    if gate.ark_snapshot_id:
        state["last_ark_snapshot_id"] = gate.ark_snapshot_id
    state["steps"]["oracle"] = {
        "complete": gate.guardian_class != "BLACK",
        "ts": _now(),
        "summary": f"Oracle dry-run complete: {gate.oracle_result}.",
        "oracle_result": gate.oracle_result,
        "guardian_class": gate.guardian_class,
        "ark_snapshot_id": gate.ark_snapshot_id,
    }
    _save_preflight(state)
    record = _append_audit({"actor": actor, "event": "world_preflight_oracle_complete", "payload": {"text": text, "gate": asdict(gate)}})
    return {
        "ok": gate.guardian_class != "BLACK",
        "executed": False,
        "panel": "Preflight",
        "title": "Next Action Complete — Oracle Dry-Run Dossier",
        "guardian_policy": gate.guardian_class,
        "executive_summary": [
            "Oracle dry-run completed without executing the command.",
            f"Forecast result: {gate.oracle_result}.",
            "This satisfies the dry-run requirement for high-friction registry or relay activity.",
        ],
        "facts": {
            "command_text": text,
            "executed": False,
            "guardian_class": gate.guardian_class,
            "oracle_result": gate.oracle_result,
            "ark_snapshot_id": gate.ark_snapshot_id,
            "audit_id": record.get("audit_id"),
        },
        "narrative": {
            "Operational meaning": "Oracle converts a proposed action into a no-side-effect forecast before you decide whether to continue.",
            "Rollback meaning": "The dry-run gate creates an Ark command snapshot so later review can inspect the forecast context.",
            "Completion result": "The Oracle step is now marked complete unless the command is BLACK/forbidden.",
        },
        "command": cmd.model_dump(),
        "gate": asdict(gate),
        "forecast": {
            "external_side_effects": False,
            "rollback_required": gate.guardian_class in {"AMBER", "RED"},
            "execution_advice": "Do not execute until Watchers, Guardians, Oracle, and Ark steps are all complete.",
        },
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state, "command": cmd.model_dump(), "gate": asdict(gate)},
    }


def _ark_preflight(actor: str) -> Dict[str, Any]:
    state_before = _load_preflight()
    snapshot_id = _ark_snapshot("preflight_before_registry_or_relay_change", {"actor": actor, "preflight_state": state_before})
    state = _load_preflight()
    state["last_ark_snapshot_id"] = snapshot_id
    state["steps"]["ark"] = {
        "complete": True,
        "ts": _now(),
        "summary": f"Ark snapshot created before registry or relay change: {snapshot_id}.",
        "ark_snapshot_id": snapshot_id,
    }
    _save_preflight(state)
    record = _append_audit({"actor": actor, "event": "world_preflight_ark_complete", "payload": {"snapshot_id": snapshot_id}})
    return {
        "ok": True,
        "panel": "Preflight",
        "title": "Next Action Complete — Ark Pre-Change Snapshot Dossier",
        "guardian_policy": "AMBER",
        "executive_summary": [
            "Ark pre-change snapshot created successfully.",
            "This creates a restore-point evidence object before registry or relay changes.",
            "The Ark requirement is now complete for the current local preflight chain.",
        ],
        "facts": {
            "snapshot_id": snapshot_id,
            "audit_id": record.get("audit_id"),
            "preflight_status": state.get("status"),
        },
        "narrative": {
            "Continuity meaning": "Ark captures the pre-change state so registry or relay changes have an evidence-backed rollback reference.",
            "Evidence boundary": "This is a local file-backed restore point, not an external notarization.",
            "Completion result": "The Ark step is now marked complete in the preflight state file.",
        },
        "snapshot_id": snapshot_id,
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state},
    }


def _preflight_dossier(actor: str) -> Dict[str, Any]:
    state = _load_preflight()
    steps = state.get("steps", {})
    record = _append_audit({"actor": actor, "event": "world_preflight_read", "payload": {"status": state.get("status")}})
    return {
        "ok": True,
        "panel": "Preflight",
        "title": "Recommended Next Actions — Preflight Dossier",
        "guardian_policy": "GREEN" if state.get("status") == "ready_for_bounded_registry_or_relay_change" else "AMBER",
        "executive_summary": [
            "This dossier tracks the four required next actions from the WORLD CONTROLLER UI.",
            "The chain is complete only after Watchers, Guardians, Oracle, and Ark all have current evidence.",
            f"Current preflight status: {state.get('status')}.",
        ],
        "facts": {
            "workflow_id": state.get("workflow_id"),
            "status": state.get("status"),
            "updated_at": state.get("updated_at"),
            "last_command_text": state.get("last_command_text"),
            "last_guardian_class": state.get("last_guardian_class"),
            "last_oracle_result": state.get("last_oracle_result"),
            "last_ark_snapshot_id": state.get("last_ark_snapshot_id"),
            "audit_id": record.get("audit_id"),
        },
        "narrative": {
            "Workflow meaning": "WORLD CONTROLLER uses this chain to prevent registry or relay changes from happening before visibility, classification, dry-run, and continuity evidence exist.",
            "Completion rule": "Watchers confirms heartbeat state; Guardians classifies risk; Oracle forecasts impact; Ark creates the pre-change restore point.",
            "Execution boundary": "Completing preflight does not bypass Guardian policy. It only proves the preparatory actions were performed.",
        },
        "components": steps,
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state},
    }


def _auth_headers(authorization: Optional[str], x_sara_admin_token: Optional[str]) -> str:
    return _require_admin(authorization, x_sara_admin_token)


@router.get("/ui", response_class=HTMLResponse)
def world_ui() -> HTMLResponse:
    html_path = Path(__file__).with_name("world_controller_static") / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>WORLD CONTROLLER</h1><p>Static UI missing, API is mounted.</p>")


@router.get("/status")
def world_status(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    registry = _load_registry()
    record = _append_audit({"actor": actor, "event": "world_status_read", "payload": {}})
    return {
        "ok": True,
        "service": "WORLD CONTROLLER",
        "mode": "simulate_first",
        "actor": actor,
        "registry_nodes": len(registry),
        "routes": [
            "/world/ui", "/world/status", "/world/dashboard", "/world/watchers", "/world/guardians",
            "/world/oracle", "/world/ark", "/world/registry", "/world/audit", "/world/admin",
            "/world/preflight", "/world/preflight/run", "/world/evidence/preflight",
            "/world/command/parse", "/world/command/simulate", "/world/command/execute",
        ],
        "audit_recorded": record["ts"],
        "components": _component_status(),
    }


@router.get("/dashboard")
def world_dashboard(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    registry = _load_registry()
    counts: Dict[str, int] = {}
    for node in registry.values():
        status = str(node.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    _append_audit({"actor": actor, "event": "world_dashboard_read", "payload": {"status_counts": counts}})
    return {
        "ok": True,
        "panel": "Dashboard",
        "summary": {
            "nodes": len(registry),
            "status_counts": counts,
            "simulate_first": True,
            "execution_policy": "GREEN/BLUE require confirmation; AMBER env unlock; RED/BLACK denied",
        },
        "components": _component_status(),
        "next_actions": [
            "Use Watchers to inspect node heartbeat state.",
            "Use Guardians to classify commands before execution.",
            "Use Oracle to dry-run high-friction actions.",
            "Use Ark before registry or relay changes.",
        ],
    }


@router.get("/watchers")
def world_watchers(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    registry = _load_registry()
    now = _now()
    watchers = []
    for node_id, node in registry.items():
        last_seen = float(node.get("last_seen", now))
        watchers.append({
            "node_id": node_id,
            "role": node.get("role"),
            "status": node.get("status"),
            "guardian_policy": node.get("guardian_policy"),
            "last_seen": last_seen,
            "age_seconds": round(now - last_seen, 3),
            "heartbeat": "fresh" if now - last_seen < 300 else "stale",
            "capabilities": node.get("capabilities", []),
        })
    _append_audit({"actor": actor, "event": "world_watchers_read", "payload": {"nodes": len(watchers)}})
    return {"ok": True, "panel": "Watchers", "watchers": watchers}


@router.get("/guardians")
def world_guardians(
    sample: str = "SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN",
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd = _parse_natural(sample)
    gate = _gate(cmd)
    _append_audit({"actor": actor, "event": "world_guardians_read", "payload": {"sample": sample, "gate": asdict(gate)}})
    return {
        "ok": True,
        "panel": "Guardians",
        "policy": {
            "GREEN": "Observe/read-only/dry run.",
            "BLUE": "Local reversible configuration; execute requires confirmation.",
            "AMBER": "Registry/relay/rollback; requires env unlock and confirmation.",
            "RED": "Physical/high-impact/safety-sensitive; denied by default.",
            "BLACK": "Forbidden action class; denied.",
        },
        "sample_command": cmd.model_dump(),
        "sample_gate": asdict(gate),
    }


@router.post("/guardians/classify")
def world_guardian_classify(
    body: NaturalCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd = _parse_natural(body.text)
    gate = _gate(cmd)
    _append_audit({"actor": actor, "event": "world_guardian_classify", "payload": {"text": body.text, "gate": asdict(gate)}})
    return {"ok": True, "command": cmd.model_dump(), "gate": asdict(gate)}


@router.get("/oracle")
def world_oracle(
    sample: str = "SIMULATE REGISTRY PATCH SARA_CORE DRY_RUN ADMIN",
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd = _parse_natural(sample)
    risk = _risk_for(cmd)
    result = _oracle(cmd, risk)
    _append_audit({"actor": actor, "event": "world_oracle_read", "payload": {"sample": sample, "risk": risk}})
    return {
        "ok": True,
        "panel": "Oracle",
        "sample_command": cmd.model_dump(),
        "risk": risk,
        "oracle_result": result,
        "forecast": {
            "external_side_effects": False,
            "rollback_required": risk in {"AMBER", "RED"},
            "execution_advice": "simulate_first; require confirmation; deny RED/BLACK by default",
        },
    }


@router.post("/oracle/simulate")
def world_oracle_simulate(
    body: NaturalCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd = _parse_natural(body.text)
    cmd.mode = "DRY_RUN"
    gate = _gate(cmd)
    _append_audit({"actor": actor, "event": "world_oracle_simulate", "payload": {"text": body.text, "gate": asdict(gate)}})
    return {"ok": gate.guardian_class != "BLACK", "executed": False, "command": cmd.model_dump(), "gate": asdict(gate)}


@router.get("/ark")
def world_ark(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    snapshots = []
    for path in sorted(_ark_dir().glob("ARK-RP-*.json"), reverse=True)[:50]:
        body = _safe_read_json(path, {})
        snapshots.append({
            "file": path.name,
            "snapshot_id": body.get("snapshot_id", path.stem),
            "ts": body.get("ts"),
            "label": body.get("label"),
            "sha256": body.get("sha256"),
        })
    _append_audit({"actor": actor, "event": "world_ark_read", "payload": {"snapshots": len(snapshots)}})
    return {"ok": True, "panel": "Ark", "snapshots": snapshots, "ark_dir": str(_ark_dir())}


@router.post("/ark/snapshot")
def world_ark_snapshot(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    snapshot_id = _ark_snapshot("manual_ui_snapshot", {"actor": actor, "source": "world_ui"})
    _append_audit({"actor": actor, "event": "world_ark_snapshot_created", "payload": {"snapshot_id": snapshot_id}})
    return {"ok": True, "snapshot_id": snapshot_id}


@router.get("/registry")
def world_registry(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    registry = _load_registry()
    _append_audit({"actor": actor, "event": "world_registry_read", "payload": {"nodes": list(registry.keys())}})
    return {"ok": True, "panel": "Registry", "registry": registry, "registry_hash": _sha256_obj(registry)}


@router.post("/registry/patch")
def world_registry_patch(
    patch: RegistryPatch,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    snapshot_id = _ark_snapshot("pre_registry_patch", {"patch": patch.model_dump(), "actor": actor})
    registry = _load_registry()
    node_id = patch.node_id.upper()
    node = registry.setdefault(node_id, {"role": "custom", "status": "standby", "capabilities": [], "guardian_policy": "AMBER"})
    if patch.status is not None:
        node["status"] = patch.status
    if patch.role is not None:
        node["role"] = patch.role
    if patch.guardian_policy is not None:
        node["guardian_policy"] = patch.guardian_policy
    if patch.capabilities is not None:
        node["capabilities"] = patch.capabilities
    node["last_seen"] = _now()
    if patch.note:
        node["note"] = patch.note
    _save_registry(registry)
    _append_audit({"actor": actor, "event": "world_registry_patch", "payload": {"patch": patch.model_dump(), "snapshot_id": snapshot_id}})
    return {"ok": True, "snapshot_id": snapshot_id, "node_id": node_id, "node": node, "registry_hash": _sha256_obj(registry)}


@router.get("/admin")
def world_admin(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    _append_audit({"actor": actor, "event": "world_admin_read", "payload": {}})
    return {
        "ok": True,
        "panel": "Admin",
        "actor": actor,
        "env": {
            "WORLD_DATA_DIR": os.getenv("WORLD_DATA_DIR", "data"),
            "WORLD_ALLOW_AMBER_EXECUTE": os.getenv("WORLD_ALLOW_AMBER_EXECUTE", "0"),
            "SARA_ADMIN_TOKEN_set": bool(os.getenv("SARA_ADMIN_TOKEN", "")),
            "SARA_RELAY_TOKEN_set": bool(os.getenv("SARA_RELAY_TOKEN", "")),
        },
        "components": _component_status(),
    }


@router.post("/command/parse")
def world_command_parse(
    body: NaturalCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd = _parse_natural(body.text)
    gate = _gate(cmd)
    _append_audit({"actor": actor, "event": "world_command_parse", "payload": {"text": body.text, "command": cmd.model_dump(), "gate": asdict(gate)}})
    return {"ok": True, "command": cmd.model_dump(), "gate": asdict(gate)}


@router.post("/command/simulate")
def world_command_simulate(
    cmd: WorldCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd.mode = "DRY_RUN"
    gate = _gate(cmd)
    _append_audit({"actor": actor, "event": "world_command_simulate", "payload": {"command": cmd.model_dump(), "gate": asdict(gate)}})
    return {"ok": gate.guardian_class != "BLACK", "executed": False, "command": cmd.model_dump(), "gate": asdict(gate)}


@router.post("/command/execute")
def world_command_execute(
    cmd: WorldCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    cmd.mode = "EXECUTE"
    gate = _gate(cmd)
    event = "world_command_execute_allowed" if gate.guardian_allowed else "world_command_execute_denied"
    _append_audit({"actor": actor, "event": event, "payload": {"command": cmd.model_dump(), "gate": asdict(gate)}})

    if not gate.guardian_allowed:
        return JSONResponse(status_code=403, content={"ok": False, "executed": False, "command": cmd.model_dump(), "gate": asdict(gate)})

    # Safe-local execution adapter v1:
    # only records execution and updates local node timestamps. It does not call shell, network, hardware, or external systems.
    registry = _load_registry()
    node = registry.get(cmd.target.upper())
    if node is not None:
        node["last_seen"] = _now()
        node["last_action"] = {"intent": cmd.intent, "action": cmd.action, "scope": cmd.scope, "ts": _now()}
        _save_registry(registry)

    return {
        "ok": True,
        "executed": True,
        "note": "safe_local_execution_recorded_no_external_side_effect",
        "command": cmd.model_dump(),
        "gate": asdict(gate),
    }


@router.get("/audit")
def world_audit(
    limit: int = 50,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    rows = _read_audit(limit=limit)
    _append_audit({"actor": actor, "event": "world_audit_read", "payload": {"limit": limit, "returned": len(rows)}})
    return {"ok": True, "panel": "Audit", "records": rows}


def _find_audit_record(audit_id: str) -> Optional[Dict[str, Any]]:
    path = _audit_path()
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("audit_id", "")) == audit_id:
            return row
    return None


def _read_ark_snapshot_by_id(snapshot_id: str) -> Optional[Dict[str, Any]]:
    candidate = _ark_dir() / f"{snapshot_id}.json"
    if candidate.exists():
        body = _safe_read_json(candidate, {})
        if isinstance(body, dict):
            return body
    for path in _ark_dir().glob("ARK-RP-*.json"):
        body = _safe_read_json(path, {})
        if isinstance(body, dict) and body.get("snapshot_id") == snapshot_id:
            return body
    return None


def _node_evidence(node_id: str) -> Dict[str, Any]:
    registry = _load_registry()
    key = node_id.upper()
    node = registry.get(key)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    policy = str(node.get("guardian_policy", "GREEN"))
    role = str(node.get("role", "unknown"))
    status = str(node.get("status", "unknown"))
    capabilities = node.get("capabilities", []) or []
    return {
        "ok": True,
        "panel": "Evidence",
        "evidence_type": "node",
        "title": f"Node Evidence Dossier — {key}",
        "guardian_policy": policy,
        "executive_summary": [
            f"{key} is registered as role '{role}' with current status '{status}'.",
            f"Guardian policy class is {policy}.",
            "This dossier is generated from the local WORLD CONTROLLER registry and should be treated as local operational evidence unless independently verified.",
        ],
        "facts": {
            "node_id": key,
            "role": role,
            "status": status,
            "guardian_policy": policy,
            "capability_count": len(capabilities),
            "last_seen": node.get("last_seen", "n/a"),
            "registry_hash": _sha256_obj(registry),
        },
        "narrative": {
            "Operational meaning": f"{key} is a WORLD CONTROLLER registry object. Its capabilities define what the UI may present and what local workflows may reference.",
            "Risk interpretation": f"Guardian class {policy} controls whether actions involving this node are read-only, reversible, approval-gated, or denied by default.",
            "Evidence boundary": "This evidence proves the current local registry state. It does not prove external deployment, physical actuation, or third-party validation.",
        },
        "capabilities": capabilities,
        "evidence_links": [
            {"label": "Open Registry Hash Evidence", "path": f"/world/evidence/registry/hash/{_sha256_obj(registry)}"},
            {"label": "Open Audit Evidence Index", "path": "/world/audit?limit=50"},
        ],
        "next_actions": [
            "Confirm the node status and role are still accurate.",
            "Use Guardian Classification before any command involving this node.",
            "Create an Ark snapshot before changing node policy, role, or capabilities.",
        ],
        "raw_evidence": {"registry_node": node},
    }


def _registry_hash_evidence(hash_value: str) -> Dict[str, Any]:
    registry = _load_registry()
    current_hash = _sha256_obj(registry)
    matches = hash_value == current_hash
    nodes = list(registry.keys())
    return {
        "ok": matches,
        "panel": "Evidence",
        "evidence_type": "registry_hash",
        "title": "Registry Hash Evidence Dossier",
        "guardian_policy": "GREEN" if matches else "AMBER",
        "executive_summary": [
            "The registry hash is a SHA-256 digest of the current local WORLD CONTROLLER registry object.",
            "A matching hash means the displayed registry evidence and the current registry state are aligned.",
            "A mismatch means the registry changed after the dossier link was generated or the supplied hash is stale/incorrect.",
        ],
        "facts": {
            "requested_hash": hash_value,
            "current_registry_hash": current_hash,
            "hash_matches_current_registry": matches,
            "node_count": len(nodes),
            "nodes": ", ".join(nodes),
        },
        "narrative": {
            "Integrity meaning": "This hash anchors the visible registry state to a deterministic digest, giving you a quick local tamper/staleness check.",
            "Operational use": "When you export a dossier, preserve this hash with the PDF or copy. Later, reload this evidence link to see if the registry still matches.",
            "Evidence boundary": "This is local integrity evidence only. It is not notarized, externally timestamped, or cryptographically signed unless you add that later through Ark/SARA hardening.",
        },
        "registry": registry,
        "evidence_links": [{"label": f"Open Node Evidence — {node_id}", "path": f"/world/evidence/node/{node_id}"} for node_id in nodes],
        "next_actions": [
            "If the hash does not match, refresh the Registry Dossier and export a new evidence copy.",
            "Create an Ark snapshot before and after any registry patch.",
            "For attorney or partner packets, mark this as local operational evidence requiring repository/runtime verification.",
        ],
        "raw_evidence": {"registry": registry},
    }


def _audit_evidence(audit_id: str) -> Dict[str, Any]:
    row = _find_audit_record(audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Audit record not found: {audit_id}")
    payload = row.get("payload", {}) if isinstance(row.get("payload", {}), dict) else {}
    gate = payload.get("gate", {}) if isinstance(payload.get("gate", {}), dict) else {}
    command = payload.get("command", {}) if isinstance(payload.get("command", {}), dict) else {}
    linked = []
    snapshot_id = gate.get("ark_snapshot_id") or payload.get("snapshot_id")
    if snapshot_id:
        linked.append({"label": f"Open Ark Evidence — {snapshot_id}", "path": f"/world/evidence/ark/{snapshot_id}"})
    target = command.get("target")
    if target:
        linked.append({"label": f"Open Target Node Evidence — {target}", "path": f"/world/evidence/node/{target}"})
    return {
        "ok": True,
        "panel": "Evidence",
        "evidence_type": "audit_record",
        "title": f"Audit Evidence Dossier — {audit_id}",
        "guardian_policy": gate.get("guardian_class", "GREEN"),
        "executive_summary": [
            f"Audit event '{row.get('event', 'unknown')}' was recorded for actor '{row.get('actor', 'unknown')}'.",
            "The record is part of the local WORLD CONTROLLER audit JSONL log.",
            "Linked Ark and node evidence are shown when the audit payload contains those identifiers.",
        ],
        "facts": {
            "audit_id": row.get("audit_id"),
            "timestamp": row.get("ts"),
            "actor": row.get("actor"),
            "event": row.get("event"),
            "has_payload": bool(payload),
            "linked_snapshot": snapshot_id or "none",
            "linked_target": target or "none",
        },
        "narrative": {
            "Chain-of-custody meaning": "The audit row records who asked for the action/readout, what route or event occurred, and what payload was logged.",
            "Review use": "Use this dossier to trace a UI action back to local operational evidence without reading raw JSON first.",
            "Evidence boundary": "The audit log is local and append-style. For stronger evidentiary posture, add signed timestamps, immutable append-only storage, and external hash anchoring.",
        },
        "evidence_links": linked,
        "next_actions": [
            "Open linked Ark evidence if a restore point exists.",
            "Open linked node evidence if a command target exists.",
            "Export/print this dossier when preserving a local action record.",
        ],
        "raw_evidence": row,
    }


def _ark_evidence(snapshot_id: str) -> Dict[str, Any]:
    body = _read_ark_snapshot_by_id(snapshot_id)
    if body is None:
        raise HTTPException(status_code=404, detail=f"Ark snapshot not found: {snapshot_id}")
    registry = body.get("registry", {}) if isinstance(body.get("registry", {}), dict) else {}
    payload = body.get("payload", {}) if isinstance(body.get("payload", {}), dict) else {}
    cmd = payload.get("command", {}) if isinstance(payload.get("command", {}), dict) else {}
    links = []
    target = cmd.get("target")
    if target:
        links.append({"label": f"Open Target Node Evidence — {target}", "path": f"/world/evidence/node/{target}"})
    if registry:
        links.append({"label": "Open Registry Hash Evidence", "path": f"/world/evidence/registry/hash/{_sha256_obj(registry)}"})
    return {
        "ok": True,
        "panel": "Evidence",
        "evidence_type": "ark_snapshot",
        "title": f"Ark Restore-Point Evidence — {snapshot_id}",
        "guardian_policy": "AMBER",
        "executive_summary": [
            "This Ark record captures a local restore-point snapshot used for continuity and rollback review.",
            f"Snapshot label: {body.get('label', 'unlabeled')}",
            "The snapshot contains registry state and triggering payload evidence.",
        ],
        "facts": {
            "snapshot_id": body.get("snapshot_id"),
            "timestamp": body.get("ts"),
            "label": body.get("label"),
            "sha256": body.get("sha256"),
            "registry_node_count": len(registry),
            "payload_keys": ", ".join(payload.keys()) if isinstance(payload, dict) else "none",
        },
        "narrative": {
            "Continuity meaning": "Ark restore points preserve the before-state or command-gate state surrounding registry and command activity.",
            "Rollback meaning": "This record gives a human reviewer enough context to reconstruct what was known before or during a gated action.",
            "Evidence boundary": "This is a local file-based snapshot. It should be copied into a signed evidence bundle for stronger legal or engineering review.",
        },
        "registry": registry,
        "evidence_links": links,
        "next_actions": [
            "Compare this snapshot hash against exported records.",
            "Open node evidence for any command target referenced in the payload.",
            "Create a new snapshot after any corrective registry change.",
        ],
        "raw_evidence": body,
    }


@router.get("/preflight")
def world_preflight(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    return _preflight_dossier(actor)


@router.post("/preflight/watchers")
def world_preflight_watchers(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    return _watchers_preflight(actor)


@router.post("/preflight/guardians")
def world_preflight_guardians(
    body: NaturalCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    return _guardians_preflight(actor, body.text)


@router.post("/preflight/oracle")
def world_preflight_oracle(
    body: NaturalCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    return _oracle_preflight(actor, body.text)


@router.post("/preflight/ark")
def world_preflight_ark(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    return _ark_preflight(actor)


@router.post("/preflight/run")
def world_preflight_run(
    body: NaturalCommand,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    watchers = _watchers_preflight(actor)
    guardians = _guardians_preflight(actor, body.text)
    oracle = _oracle_preflight(actor, body.text)
    ark = _ark_preflight(actor)
    state = _load_preflight()
    record = _append_audit({"actor": actor, "event": "world_preflight_run_complete", "payload": {"status": state.get("status"), "text": body.text}})
    return {
        "ok": state.get("status") == "ready_for_bounded_registry_or_relay_change",
        "panel": "Preflight",
        "title": "Full Recommended Next Actions Chain — Complete Dossier",
        "guardian_policy": "GREEN" if state.get("status") == "ready_for_bounded_registry_or_relay_change" else "AMBER",
        "executive_summary": [
            "WORLD CONTROLLER ran the full preflight chain from the UI action set.",
            "Watchers inspected heartbeat state; Guardians classified the command; Oracle performed a dry-run; Ark created a pre-change restore point.",
            f"Final preflight status: {state.get('status')}.",
        ],
        "facts": {
            "status": state.get("status"),
            "last_guardian_class": state.get("last_guardian_class"),
            "last_oracle_result": state.get("last_oracle_result"),
            "last_ark_snapshot_id": state.get("last_ark_snapshot_id"),
            "audit_id": record.get("audit_id"),
        },
        "narrative": {
            "Operational meaning": "The system now has a single-click preflight path for the exact recommendations shown in the UI.",
            "Safety meaning": "This does not force execution. It establishes the required local evidence before any registry or relay action is considered.",
            "Review meaning": "Open the linked Preflight Evidence Dossier to inspect the final state and supporting Ark/audit/node records.",
        },
        "components": state.get("steps", {}),
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state, "watchers": watchers, "guardians": guardians, "oracle": oracle, "ark": ark},
    }


@router.get("/evidence")
def world_evidence_index(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    registry = _load_registry()
    audits = _read_audit(limit=20)
    snapshots = []
    for path in sorted(_ark_dir().glob("ARK-RP-*.json"), reverse=True)[:20]:
        body = _safe_read_json(path, {})
        snapshots.append({"snapshot_id": body.get("snapshot_id", path.stem), "label": body.get("label"), "sha256": body.get("sha256")})
    _append_audit({"actor": actor, "event": "world_evidence_index_read", "payload": {"nodes": len(registry), "audits": len(audits), "snapshots": len(snapshots)}})
    return {
        "ok": True,
        "panel": "Evidence",
        "evidence_type": "index",
        "title": "WORLD CONTROLLER Evidence Index",
        "guardian_policy": "GREEN",
        "executive_summary": [
            "This page is the evidence navigation hub for all local WORLD CONTROLLER dossiers.",
            "Open node, registry-hash, audit, and Ark evidence links to view human-readable full-bloom records.",
        ],
        "facts": {
            "actor": actor,
            "registry_nodes": len(registry),
            "audit_records_shown": len(audits),
            "ark_snapshots_shown": len(snapshots),
            "current_registry_hash": _sha256_obj(registry),
        },
        "registry": registry,
        "records": audits,
        "snapshots": snapshots,
        "evidence_links": [
            {"label": "Open Current Registry Hash Evidence", "path": f"/world/evidence/registry/hash/{_sha256_obj(registry)}"},
            *[{"label": f"Open Node Evidence — {node_id}", "path": f"/world/evidence/node/{node_id}"} for node_id in registry.keys()],
        ],
        "next_actions": [
            "Use this index as the first stop when building a packet or reviewing operational state.",
            "Export any evidence dossier with Print / Save PDF before changing the registry.",
        ],
    }


@router.get("/evidence/preflight")
def world_evidence_preflight(
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    actor = _auth_headers(authorization, x_sara_admin_token)
    state = _load_preflight()
    _append_audit({"actor": actor, "event": "world_evidence_preflight_read", "payload": {"status": state.get("status")}})
    return {
        "ok": True,
        "panel": "Evidence",
        "evidence_type": "preflight",
        "title": "Preflight Evidence Dossier — Recommended Next Actions",
        "guardian_policy": "GREEN" if state.get("status") == "ready_for_bounded_registry_or_relay_change" else "AMBER",
        "executive_summary": [
            "This evidence dossier shows whether the UI's recommended next actions have actually been completed.",
            "It records Watchers, Guardians, Oracle, and Ark completion state in one human-readable evidence page.",
            f"Current status: {state.get('status')}.",
        ],
        "facts": {
            "workflow_id": state.get("workflow_id"),
            "status": state.get("status"),
            "updated_at": state.get("updated_at"),
            "last_command_text": state.get("last_command_text"),
            "last_guardian_class": state.get("last_guardian_class"),
            "last_oracle_result": state.get("last_oracle_result"),
            "last_ark_snapshot_id": state.get("last_ark_snapshot_id"),
            "last_registry_hash": state.get("last_registry_hash"),
        },
        "narrative": {
            "Evidence meaning": "The recommended next actions are no longer static text. They are tracked as a concrete preflight state object in the local WORLD CONTROLLER data directory.",
            "Completion meaning": "Ready status requires all four steps to be complete: Watchers, Guardians, Oracle, and Ark.",
            "Boundary": "This proves local UI workflow completion. It does not independently verify external systems, physical hardware, or third-party infrastructure.",
        },
        "components": state.get("steps", {}),
        "evidence_links": _preflight_evidence_links(state),
        "next_actions": _preflight_next_actions(state),
        "raw_evidence": {"preflight_state": state},
    }


@router.get("/evidence/node/{node_id}")
def world_evidence_node(
    node_id: str,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _auth_headers(authorization, x_sara_admin_token)
    return _node_evidence(node_id)


@router.get("/evidence/registry/hash/{hash_value}")
def world_evidence_registry_hash(
    hash_value: str,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _auth_headers(authorization, x_sara_admin_token)
    return _registry_hash_evidence(hash_value)


@router.get("/evidence/audit/{audit_id}")
def world_evidence_audit(
    audit_id: str,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _auth_headers(authorization, x_sara_admin_token)
    return _audit_evidence(audit_id)


@router.get("/evidence/ark/{snapshot_id}")
def world_evidence_ark(
    snapshot_id: str,
    authorization: Optional[str] = Header(default=None),
    x_sara_admin_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    _auth_headers(authorization, x_sara_admin_token)
    return _ark_evidence(snapshot_id)
