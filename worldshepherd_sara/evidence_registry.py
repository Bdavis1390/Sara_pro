from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterator, Literal

from worldshepherd_sara.evidence_calibration import validate_calibration_record
from worldshepherd_sara.evidence_contract import (
    EvidenceValidationError,
    validate_claim_record,
    validate_experiment_record,
)
from worldshepherd_sara.evidence_material import validate_material_record

RecordKind = Literal["experiment", "claim", "calibration", "material"]
RECORD_KINDS: tuple[RecordKind, ...] = (
    "experiment",
    "claim",
    "calibration",
    "material",
)


class EvidenceRegistryError(RuntimeError):
    """Base error for append-only evidence registry operations."""


class DuplicateEvidenceId(EvidenceRegistryError):
    """Raised when a caller attempts to reuse an existing record identifier."""


class EvidenceNotFound(EvidenceRegistryError):
    """Raised when a record or supersession target cannot be found."""


class EvidenceReferenceError(EvidenceRegistryError):
    """Raised when a record references missing, ambiguous, or incompatible evidence."""


class EvidenceSupersessionError(EvidenceRegistryError):
    """Raised when supersession would violate append-only lineage rules."""


class EvidenceDigestMismatch(EvidenceRegistryError):
    """Raised when a local evidence object does not match its declared digest."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_id(kind: RecordKind, payload: Dict[str, Any]) -> str:
    if kind == "experiment":
        return payload["experiment_id"]
    if kind == "claim":
        return payload["claim_id"]
    if kind == "calibration":
        return payload["calibration_id"]
    return payload["material_batch_id"]


def _normalize_sha256(value: str) -> str | None:
    candidate = value.strip().lower()
    if candidate.startswith("sha256:"):
        candidate = candidate.split(":", 1)[1]
    if len(candidate) != 64 or any(ch not in "0123456789abcdef" for ch in candidate):
        return None
    return candidate


def verify_local_raw_digest(payload: Dict[str, Any]) -> Dict[str, Any]:
    raw = payload.get("raw_data") or {}
    location = raw.get("location")
    digest_text = raw.get("digest")
    if not isinstance(location, str) or not isinstance(digest_text, str):
        return {"status": "UNVERIFIED", "reason": "missing location or digest"}
    expected = _normalize_sha256(digest_text)
    if expected is None:
        return {"status": "UNVERIFIED", "reason": "digest is not SHA-256"}
    if "://" in location and not location.startswith("file://"):
        return {"status": "UNVERIFIED", "reason": "remote evidence object"}
    path = Path(location[7:] if location.startswith("file://") else location)
    if not path.is_file():
        return {"status": "UNVERIFIED", "reason": "local evidence object not present"}
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise EvidenceDigestMismatch(
            f"raw-data digest mismatch for {path}: expected {expected}, got {actual}"
        )
    return {"status": "VERIFIED", "algorithm": "sha256", "digest": actual}


class EvidenceRegistry:
    """Append-only scientific evidence and engineering provenance registry."""

    def __init__(self, data_dir: Path | str):
        self.root = Path(data_dir) / "evidence"
        self.root.mkdir(parents=True, exist_ok=True)
        self.paths = {
            "experiment": self.root / "experiments.jsonl",
            "claim": self.root / "claims.jsonl",
            "calibration": self.root / "calibrations.jsonl",
            "material": self.root / "materials.jsonl",
        }
        self._lock = RLock()

    def _validate(self, kind: RecordKind, payload: Dict[str, Any]) -> Dict[str, Any]:
        if kind == "experiment":
            return validate_experiment_record(payload)
        if kind == "claim":
            return validate_claim_record(payload)
        if kind == "calibration":
            return validate_calibration_record(payload)
        if kind == "material":
            return validate_material_record(payload)
        raise EvidenceValidationError("unsupported evidence record kind")

    def _iter_envelopes(self, kind: RecordKind) -> Iterator[Dict[str, Any]]:
        path = self.paths[kind]
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield item

    def _id_index(self, kind: RecordKind) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for envelope in self._iter_envelopes(kind):
            payload = envelope.get("record")
            if not isinstance(payload, dict):
                continue
            try:
                result[_record_id(kind, payload)] = envelope
            except KeyError:
                continue
        return result

    def _all_id_locations(self) -> Dict[str, list[tuple[RecordKind, Dict[str, Any]]]]:
        result: Dict[str, list[tuple[RecordKind, Dict[str, Any]]]] = {}
        for kind in RECORD_KINDS:
            for identifier, envelope in self._id_index(kind).items():
                result.setdefault(identifier, []).append((kind, envelope))
        return result

    def _resolve_record(self, record_id: str) -> tuple[RecordKind, Dict[str, Any]]:
        matches = self._all_id_locations().get(record_id, [])
        if not matches:
            raise EvidenceReferenceError(f"referenced evidence record does not exist: {record_id}")
        if len(matches) != 1:
            raise EvidenceReferenceError(f"referenced evidence record is ambiguous: {record_id}")
        return matches[0]

    @staticmethod
    def _envelope_evidence_classes(kind: RecordKind, envelope: Dict[str, Any]) -> set[str]:
        if kind == "calibration":
            return {"MEASURED"}
        record = envelope.get("record") or {}
        if kind == "experiment":
            values = record.get("evidence_class", [])
        elif kind == "claim":
            values = record.get("evidence_classes", [])
        else:
            values = []
            values.extend(
                observation.get("evidence_class")
                for observation in record.get("microstructure_observations", [])
                if isinstance(observation, dict)
            )
            values.extend(
                prop.get("evidence_class")
                for prop in record.get("properties", [])
                if isinstance(prop, dict)
            )
        return {str(value) for value in values if isinstance(value, str)}

    def _validate_experiment_references(self, payload: Dict[str, Any]) -> None:
        if "MEASURED" not in payload.get("evidence_class", []):
            return
        calibration_ids = payload.get("calibration_ids", [])
        if not calibration_ids:
            raise EvidenceReferenceError(
                "MEASURED experiment requires at least one registered calibration_id"
            )
        calibration_set = set(calibration_ids)
        for calibration_id in calibration_ids:
            kind, _ = self._resolve_record(calibration_id)
            if kind != "calibration":
                raise EvidenceReferenceError(
                    f"experiment calibration_id must resolve to calibration record: {calibration_id}"
                )
        for sensor in payload.get("sensor_manifest", []):
            sensor_calibration = sensor.get("calibration_id")
            if sensor_calibration not in calibration_set:
                raise EvidenceReferenceError(
                    f"sensor calibration_id is not declared in experiment calibration_ids: {sensor_calibration}"
                )
            kind, _ = self._resolve_record(sensor_calibration)
            if kind != "calibration":
                raise EvidenceReferenceError(
                    f"sensor calibration_id must resolve to calibration record: {sensor_calibration}"
                )

    def _validate_claim_references(self, payload: Dict[str, Any]) -> None:
        supporting_ids = payload.get("supporting_record_ids", [])
        contradicting_ids = payload.get("contradicting_record_ids", [])
        replication_ids = payload.get("replication_ids", [])
        support_classes: set[str] = set()
        for record_id in supporting_ids:
            kind, envelope = self._resolve_record(record_id)
            support_classes.update(self._envelope_evidence_classes(kind, envelope))
        for record_id in contradicting_ids:
            self._resolve_record(record_id)
        for record_id in replication_ids:
            self._resolve_record(record_id)
        if "MEASURED" in payload.get("evidence_classes", []) and "MEASURED" not in support_classes:
            raise EvidenceReferenceError(
                "claim declares MEASURED evidence but no supporting record is actually MEASURED"
            )
        if payload.get("confidence_status") == "INDEPENDENTLY_REPRODUCED" and not replication_ids:
            raise EvidenceReferenceError(
                "INDEPENDENTLY_REPRODUCED confidence requires resolvable replication_ids"
            )
        uncertainty_reference = payload.get("uncertainty_reference")
        if payload.get("quantitative") and "MEASURED" in payload.get("evidence_classes", []):
            base_id = str(uncertainty_reference).split("#", 1)[0]
            kind, envelope = self._resolve_record(base_id)
            if kind not in {"experiment", "calibration"}:
                raise EvidenceReferenceError(
                    "quantitative measured uncertainty_reference must resolve to an experiment or calibration"
                )
            if kind == "experiment" and "MEASURED" not in self._envelope_evidence_classes(kind, envelope):
                raise EvidenceReferenceError(
                    "quantitative measured uncertainty_reference experiment must be MEASURED"
                )

    def _validate_material_references(self, payload: Dict[str, Any]) -> None:
        for feedstock_id in payload.get("feedstock_ids", []):
            kind, _ = self._resolve_record(feedstock_id)
            if kind != "material":
                raise EvidenceReferenceError(
                    f"feedstock_id must resolve to material record: {feedstock_id}"
                )

        for collection_name in ("microstructure_observations", "properties"):
            for item in payload.get(collection_name, []):
                evidence_class = item.get("evidence_class")
                source_ids = item.get("source_record_ids", [])
                source_classes: set[str] = set()
                for source_id in source_ids:
                    kind, envelope = self._resolve_record(source_id)
                    source_classes.update(self._envelope_evidence_classes(kind, envelope))
                if evidence_class == "MEASURED" and "MEASURED" not in source_classes:
                    raise EvidenceReferenceError(
                        f"{collection_name} item declares MEASURED but has no measured source record"
                    )
                uncertainty_reference = item.get("uncertainty_reference")
                if evidence_class == "MEASURED" and uncertainty_reference:
                    base_id = str(uncertainty_reference).split("#", 1)[0]
                    kind, envelope = self._resolve_record(base_id)
                    if kind not in {"experiment", "calibration"}:
                        raise EvidenceReferenceError(
                            "measured material uncertainty_reference must resolve to experiment or calibration"
                        )
                    if kind == "experiment" and "MEASURED" not in self._envelope_evidence_classes(kind, envelope):
                        raise EvidenceReferenceError(
                            "measured material uncertainty_reference experiment must be MEASURED"
                        )

    def _superseded_ids(self, kind: RecordKind) -> set[str]:
        return {
            str(envelope["supersedes_record_id"])
            for envelope in self._iter_envelopes(kind)
            if envelope.get("supersedes_record_id")
        }

    def append(
        self,
        kind: RecordKind,
        payload: Dict[str, Any],
        *,
        actor: str,
        supersedes_record_id: str | None = None,
    ) -> Dict[str, Any]:
        validated = dict(self._validate(kind, payload))
        identifier = _record_id(kind, validated)
        with self._lock:
            if identifier in self._all_id_locations():
                raise DuplicateEvidenceId(f"evidence id already exists: {identifier}")
            index = self._id_index(kind)
            if supersedes_record_id:
                if supersedes_record_id == identifier:
                    raise EvidenceSupersessionError("record cannot supersede itself")
                if supersedes_record_id not in index:
                    raise EvidenceNotFound(
                        f"supersession target does not exist in the same record class: {supersedes_record_id}"
                    )
                if supersedes_record_id in self._superseded_ids(kind):
                    raise EvidenceSupersessionError(
                        f"supersession target already has a successor: {supersedes_record_id}"
                    )

            if kind == "experiment":
                self._validate_experiment_references(validated)
            elif kind == "claim":
                self._validate_claim_references(validated)
            elif kind == "material":
                self._validate_material_references(validated)

            digest_verification = (
                verify_local_raw_digest(validated)
                if kind in {"experiment", "calibration"}
                else {"status": "NOT_APPLICABLE"}
            )
            envelope = {
                "registry_version": "WS-EVIDENCE-0.3",
                "record_type": kind,
                "record_id": identifier,
                "stored_at_utc": _utc_now(),
                "actor": actor,
                "supersedes_record_id": supersedes_record_id,
                "digest_verification": digest_verification,
                "record": validated,
            }
            with self.paths[kind].open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(envelope, sort_keys=True) + "\n")
            return envelope

    def get(self, kind: RecordKind, record_id: str) -> Dict[str, Any]:
        envelope = self._id_index(kind).get(record_id)
        if envelope is None:
            raise EvidenceNotFound(f"{kind} record not found: {record_id}")
        result = dict(envelope)
        result["is_superseded"] = record_id in self._superseded_ids(kind)
        return result

    def iter_all(self) -> Iterator[Dict[str, Any]]:
        for kind in RECORD_KINDS:
            yield from self._iter_envelopes(kind)

    def export_jsonl(self) -> str:
        return "".join(json.dumps(item, sort_keys=True) + "\n" for item in self.iter_all())

    def metrics(self) -> Dict[str, Any]:
        experiments = list(self._iter_envelopes("experiment"))
        claims = list(self._iter_envelopes("claim"))
        calibrations = list(self._iter_envelopes("calibration"))
        materials = list(self._iter_envelopes("material"))
        evidence_counts: Dict[str, int] = {}
        result_counts: Dict[str, int] = {}
        claim_counts: Dict[str, int] = {}
        confidence_counts: Dict[str, int] = {}
        calibration_counts: Dict[str, int] = {}
        material_role_counts: Dict[str, int] = {}

        for envelope in experiments:
            record = envelope.get("record", {})
            for evidence_class in record.get("evidence_class", []):
                evidence_counts[evidence_class] = evidence_counts.get(evidence_class, 0) + 1
            result_class = record.get("result_class")
            if result_class:
                result_counts[result_class] = result_counts.get(result_class, 0) + 1
        for envelope in claims:
            record = envelope.get("record", {})
            claim_class = record.get("claim_class")
            confidence = record.get("confidence_status")
            if claim_class:
                claim_counts[claim_class] = claim_counts.get(claim_class, 0) + 1
            if confidence:
                confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
        for envelope in calibrations:
            calibration_type = envelope.get("record", {}).get("calibration_type")
            if calibration_type:
                calibration_counts[calibration_type] = calibration_counts.get(calibration_type, 0) + 1
        for envelope in materials:
            role = envelope.get("record", {}).get("batch_role")
            if role:
                material_role_counts[role] = material_role_counts.get(role, 0) + 1

        return {
            "registry_version": "WS-EVIDENCE-0.3",
            "experiments": len(experiments),
            "claims": len(claims),
            "calibrations": len(calibrations),
            "materials": len(materials),
            "superseded_experiments": len(self._superseded_ids("experiment")),
            "superseded_claims": len(self._superseded_ids("claim")),
            "superseded_calibrations": len(self._superseded_ids("calibration")),
            "superseded_materials": len(self._superseded_ids("material")),
            "evidence_classes": evidence_counts,
            "result_classes": result_counts,
            "claim_classes": claim_counts,
            "confidence_states": confidence_counts,
            "calibration_types": calibration_counts,
            "material_roles": material_role_counts,
        }
