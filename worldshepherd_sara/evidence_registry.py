from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, Iterator, Literal

from worldshepherd_sara.evidence_contract import (
    EvidenceValidationError,
    validate_claim_record,
    validate_experiment_record,
)

RecordKind = Literal["experiment", "claim"]


class EvidenceRegistryError(RuntimeError):
    """Base error for append-only evidence registry operations."""


class DuplicateEvidenceId(EvidenceRegistryError):
    """Raised when a caller attempts to reuse an existing record identifier."""


class EvidenceNotFound(EvidenceRegistryError):
    """Raised when a record or supersession target cannot be found."""


class EvidenceSupersessionError(EvidenceRegistryError):
    """Raised when supersession would violate append-only lineage rules."""


class EvidenceDigestMismatch(EvidenceRegistryError):
    """Raised when a local evidence object does not match its declared digest."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _record_id(kind: RecordKind, payload: Dict[str, Any]) -> str:
    return payload["experiment_id"] if kind == "experiment" else payload["claim_id"]


def _normalize_sha256(value: str) -> str | None:
    candidate = value.strip().lower()
    if candidate.startswith("sha256:"):
        candidate = candidate.split(":", 1)[1]
    if len(candidate) != 64 or any(ch not in "0123456789abcdef" for ch in candidate):
        return None
    return candidate


def verify_local_raw_digest(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Verify a local raw-data object when it is addressable on this host.

    Remote or absent paths remain explicitly UNVERIFIED rather than being treated as
    verified. A local existing file with a declared SHA-256 digest must match.
    """

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
    """Append-only experiment and claim registry.

    Records are never updated in place. Corrections use a new identifier plus
    ``supersedes_record_id``. The original record remains retrievable forever.
    """

    def __init__(self, data_dir: Path | str):
        self.root = Path(data_dir) / "evidence"
        self.root.mkdir(parents=True, exist_ok=True)
        self.paths = {
            "experiment": self.root / "experiments.jsonl",
            "claim": self.root / "claims.jsonl",
        }
        self._lock = RLock()

    def _validate(self, kind: RecordKind, payload: Dict[str, Any]) -> Dict[str, Any]:
        if kind == "experiment":
            return validate_experiment_record(payload)
        if kind == "claim":
            return validate_claim_record(payload)
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
            index = self._id_index(kind)
            if identifier in index:
                raise DuplicateEvidenceId(f"{kind} id already exists: {identifier}")

            if supersedes_record_id:
                if supersedes_record_id == identifier:
                    raise EvidenceSupersessionError("record cannot supersede itself")
                if supersedes_record_id not in index:
                    raise EvidenceNotFound(
                        f"supersession target does not exist: {supersedes_record_id}"
                    )
                if supersedes_record_id in self._superseded_ids(kind):
                    raise EvidenceSupersessionError(
                        f"supersession target already has a successor: {supersedes_record_id}"
                    )

            digest_verification = (
                verify_local_raw_digest(validated)
                if kind == "experiment"
                else {"status": "NOT_APPLICABLE"}
            )

            envelope = {
                "registry_version": "WS-EVIDENCE-0.1",
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
        for kind in ("experiment", "claim"):
            yield from self._iter_envelopes(kind)  # type: ignore[arg-type]

    def export_jsonl(self) -> str:
        return "".join(json.dumps(item, sort_keys=True) + "\n" for item in self.iter_all())

    def metrics(self) -> Dict[str, Any]:
        experiments = list(self._iter_envelopes("experiment"))
        claims = list(self._iter_envelopes("claim"))

        evidence_counts: Dict[str, int] = {}
        result_counts: Dict[str, int] = {}
        claim_counts: Dict[str, int] = {}
        confidence_counts: Dict[str, int] = {}

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

        return {
            "registry_version": "WS-EVIDENCE-0.1",
            "experiments": len(experiments),
            "claims": len(claims),
            "superseded_experiments": len(self._superseded_ids("experiment")),
            "superseded_claims": len(self._superseded_ids("claim")),
            "evidence_classes": evidence_counts,
            "result_classes": result_counts,
            "claim_classes": claim_counts,
            "confidence_states": confidence_counts,
        }
