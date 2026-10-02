"""Append-only, hash-chained EM observation provenance ledger.

The ledger records observations; it does not authorize actions.  Each record binds
its observation digest to the previous record digest so later alteration is
observable during read-back verification.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .em_intelligence import EMObservation


EM_OBSERVATION_LEDGER_SCHEMA = "worldshepherd.em-observation-ledger.v0.1"


class EMObservationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[EM_OBSERVATION_LEDGER_SCHEMA] = EM_OBSERVATION_LEDGER_SCHEMA
    sequence: int = Field(ge=1)
    observation: EMObservation
    observation_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    previous_record_digest: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    record_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def observation_digest(observation: EMObservation) -> str:
    return _sha256(observation.model_dump(mode="json"))


def _record_digest(
    *,
    sequence: int,
    observation_digest_value: str,
    previous_record_digest: str | None,
) -> str:
    return _sha256(
        {
            "schema_version": EM_OBSERVATION_LEDGER_SCHEMA,
            "sequence": sequence,
            "observation_digest": observation_digest_value,
            "previous_record_digest": previous_record_digest,
        }
    )


def validate_observation_shape(observation: EMObservation) -> None:
    """Reject inconsistent frequency-domain channel arrays before persistence."""

    n = len(observation.frequency_GHz)
    channels = {
        "te_real": len(observation.te_real),
        "te_imag": len(observation.te_imag),
        "tm_real": len(observation.tm_real),
        "tm_imag": len(observation.tm_imag),
    }

    populated = {name: size for name, size in channels.items() if size > 0}
    if populated and n == 0:
        raise ValueError("frequency_GHz is required when spectral channels are populated")

    for name, size in populated.items():
        if size != n:
            raise ValueError(
                f"{name} length {size} does not match frequency_GHz length {n}"
            )


class EMObservationLedger:
    """Minimal append-only JSONL ledger with fsync and chain verification."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    def read_all(self) -> list[EMObservationEnvelope]:
        if not self.path.exists():
            return []

        records: list[EMObservationEnvelope] = []
        previous: str | None = None
        seen_ids: set[str] = set()

        with self.path.open("r", encoding="utf-8") as handle:
            for expected_sequence, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                envelope = EMObservationEnvelope.model_validate_json(line)

                if envelope.sequence != expected_sequence:
                    raise ValueError("EM observation ledger sequence mismatch")
                if envelope.previous_record_digest != previous:
                    raise ValueError("EM observation ledger previous-record digest mismatch")
                if envelope.observation.observation_id in seen_ids:
                    raise ValueError("duplicate EM observation_id in ledger")

                validate_observation_shape(envelope.observation)
                expected_observation_digest = observation_digest(envelope.observation)
                if envelope.observation_digest != expected_observation_digest:
                    raise ValueError("EM observation digest mismatch")

                expected_record_digest = _record_digest(
                    sequence=envelope.sequence,
                    observation_digest_value=envelope.observation_digest,
                    previous_record_digest=envelope.previous_record_digest,
                )
                if envelope.record_digest != expected_record_digest:
                    raise ValueError("EM observation record digest mismatch")

                records.append(envelope)
                seen_ids.add(envelope.observation.observation_id)
                previous = envelope.record_digest

        return records

    def append(self, observation: EMObservation) -> EMObservationEnvelope:
        validate_observation_shape(observation)
        records = self.read_all()

        if any(
            record.observation.observation_id == observation.observation_id
            for record in records
        ):
            raise ValueError("duplicate EM observation_id")

        sequence = len(records) + 1
        previous = records[-1].record_digest if records else None
        obs_digest = observation_digest(observation)
        rec_digest = _record_digest(
            sequence=sequence,
            observation_digest_value=obs_digest,
            previous_record_digest=previous,
        )

        envelope = EMObservationEnvelope(
            sequence=sequence,
            observation=observation,
            observation_digest=obs_digest,
            previous_record_digest=previous,
            record_digest=rec_digest,
        )

        line = json.dumps(
            envelope.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ) + "\n"

        fd = os.open(
            self.path,
            os.O_WRONLY | os.O_CREAT | os.O_APPEND,
            0o600,
        )
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

        return envelope
