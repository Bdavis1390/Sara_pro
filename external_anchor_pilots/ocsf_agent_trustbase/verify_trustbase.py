#!/usr/bin/env python3
"""
Provisional semantic conformance checker for OCSF issue #1724
("agent trust-base inventory, applying record_integrity per emission").

This is intentionally non-normative. It validates structural invariants that
are already discussed in the issue thread and grounded in existing OCSF
concepts (`metadata.uid`, `ai_agent.instance_uid`, `record_integrity`,
`attestation.chain_uid`, `prev_event`, and fingerprint objects).

It does NOT attempt to implement OCSF canonical serialization or cryptographic
signature verification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

FORBIDDEN_SECRET_KEYS = {
    "secret", "password", "passwd", "private_key", "privatekey",
    "api_key", "apikey", "access_token", "refresh_token", "bearer_token",
    "credential_material", "client_secret"
}

LOCAL_ARTIFACT_KINDS = {"adapter", "tool_schema", "policy_bundle", "charter"}
REMOTE_MODEL_KINDS = {"hosted_model", "remote_model"}


def _walk(obj: Any, path: str = "$") -> Iterable[Tuple[str, str, Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}"
            yield p, str(k).lower(), v
            yield from _walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")


def _attestation(event: Dict[str, Any]) -> Dict[str, Any] | None:
    al = event.get("attestation_list")
    if isinstance(al, list) and al:
        a = al[0]
        return a if isinstance(a, dict) else None
    return None


def _fingerprint_present(obj: Any) -> bool:
    return (
        isinstance(obj, dict)
        and isinstance(obj.get("fingerprint"), dict)
        and bool(obj["fingerprint"].get("value"))
    )


def _validate_event_shape(event: Dict[str, Any], idx: int) -> List[str]:
    errors: List[str] = []
    uid = ((event.get("metadata") or {}).get("uid"))
    if not uid:
        errors.append(f"event[{idx}]: metadata.uid is required")

    agent = event.get("ai_agent") or {}
    instance_uid = agent.get("instance_uid")
    if not instance_uid:
        errors.append(f"event[{idx}]: ai_agent.instance_uid is required")

    phase = event.get("phase")
    if phase not in {"admission", "closure"}:
        errors.append(f"event[{idx}]: phase must be 'admission' or 'closure'")

    att = _attestation(event)
    if not att:
        errors.append(f"event[{idx}]: attestation_list[0] is required")
    else:
        chain_uid = att.get("chain_uid")
        if not chain_uid:
            errors.append(f"event[{idx}]: attestation.chain_uid is required")
        elif instance_uid and chain_uid != instance_uid:
            errors.append(
                f"event[{idx}]: attestation.chain_uid must equal ai_agent.instance_uid"
            )

        fp = att.get("fingerprint")
        if not isinstance(fp, dict) or not fp.get("value"):
            errors.append(f"event[{idx}]: attestation.fingerprint.value is required")
        elif str(fp.get("value")).strip().upper() == "GENESIS":
            errors.append(
                f"event[{idx}]: genesis sentinel is invalid; genesis omits prev_event"
            )

    trust = event.get("trust_base") or {}
    for side in ("declared", "observed"):
        side_obj = trust.get(side)
        if not isinstance(side_obj, dict):
            errors.append(f"event[{idx}]: trust_base.{side} object is required")
            continue
        artifacts = side_obj.get("artifacts", [])
        if artifacts is None:
            artifacts = []
        if not isinstance(artifacts, list):
            errors.append(f"event[{idx}]: trust_base.{side}.artifacts must be a list")
        else:
            for j, artifact in enumerate(artifacts):
                if not isinstance(artifact, dict):
                    errors.append(
                        f"event[{idx}]: trust_base.{side}.artifacts[{j}] must be an object"
                    )
                    continue
                kind = artifact.get("kind")
                if kind in LOCAL_ARTIFACT_KINDS and not _fingerprint_present(artifact):
                    errors.append(
                        f"event[{idx}]: local artifact {side}.artifacts[{j}] "
                        f"({kind}) requires fingerprint.value"
                    )
                if kind in REMOTE_MODEL_KINDS:
                    model = artifact.get("ai_model") or {}
                    missing = [k for k in ("ai_provider", "name", "version") if not model.get(k)]
                    if missing:
                        errors.append(
                            f"event[{idx}]: remote model {side}.artifacts[{j}] "
                            f"requires ai_model.{','.join(missing)}"
                        )

    for path, key, value in _walk(event):
        if key in FORBIDDEN_SECRET_KEYS:
            errors.append(
                f"event[{idx}]: raw credential material key '{key}' is forbidden at {path}; "
                "use references/identifiers and scopes only"
            )
    return errors


def validate_case(case: Dict[str, Any]) -> List[str]:
    events = case.get("events")
    if not isinstance(events, list) or not events:
        return ["case: non-empty events list is required"]

    errors: List[str] = []
    seen_uids = set()
    by_instance: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}

    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"event[{idx}]: event must be an object")
            continue
        errors.extend(_validate_event_shape(event, idx))

        uid = ((event.get("metadata") or {}).get("uid"))
        if uid:
            if uid in seen_uids:
                errors.append(f"event[{idx}]: duplicate metadata.uid '{uid}'")
            seen_uids.add(uid)

        instance_uid = ((event.get("ai_agent") or {}).get("instance_uid"))
        if instance_uid:
            by_instance.setdefault(instance_uid, []).append((idx, event))

    for instance_uid, seq in by_instance.items():
        previous_event = None
        open_admission = 0

        for ordinal, (idx, event) in enumerate(seq):
            att = _attestation(event) or {}
            prev = att.get("prev_event")
            phase = event.get("phase")

            if ordinal == 0:
                if prev not in (None, {}):
                    errors.append(
                        f"event[{idx}]: genesis event for instance '{instance_uid}' must omit prev_event"
                    )
            else:
                prev_uid = (prev or {}).get("uid") if isinstance(prev, dict) else None
                expected_uid = ((previous_event or {}).get("metadata") or {}).get("uid")
                if not prev_uid:
                    errors.append(
                        f"event[{idx}]: non-genesis event for instance '{instance_uid}' "
                        "requires prev_event.uid"
                    )
                elif prev_uid != expected_uid:
                    errors.append(
                        f"event[{idx}]: prev_event.uid '{prev_uid}' does not match "
                        f"preceding metadata.uid '{expected_uid}'"
                    )
                prev_fp = (prev or {}).get("fingerprint") if isinstance(prev, dict) else None
                expected_fp = ((_attestation(previous_event or {}) or {}).get("fingerprint"))
                if not isinstance(prev_fp, dict) or not prev_fp.get("value"):
                    errors.append(f"event[{idx}]: prev_event.fingerprint.value is required")
                elif isinstance(expected_fp, dict) and prev_fp.get("value") != expected_fp.get("value"):
                    errors.append(
                        f"event[{idx}]: prev_event.fingerprint.value does not match preceding fingerprint"
                    )

            if phase == "admission":
                open_admission += 1
            elif phase == "closure":
                if open_admission <= 0:
                    errors.append(
                        f"event[{idx}]: closure has no preceding unmatched admission "
                        f"for instance '{instance_uid}'"
                    )
                else:
                    open_admission -= 1

            previous_event = event

        if open_admission:
            errors.append(
                f"instance '{instance_uid}': {open_admission} admission emission(s) have no closure"
            )

    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("fixture", type=Path, help="JSON file containing {'cases': [...]}")
    args = p.parse_args()

    data = json.loads(args.fixture.read_text())
    cases = data.get("cases", [])
    if not cases:
        raise SystemExit("fixture must contain non-empty 'cases' list")

    failures = 0
    for case in cases:
        name = case.get("name", "<unnamed>")
        expected = case.get("expected", "pass")
        errors = validate_case(case)
        actual = "pass" if not errors else "fail"
        ok = actual == expected
        marker = "PASS" if ok else "MISMATCH"
        print(f"[{marker}] {name}: expected={expected} actual={actual}")
        for err in errors:
            print(f"  - {err}")
        if not ok:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
