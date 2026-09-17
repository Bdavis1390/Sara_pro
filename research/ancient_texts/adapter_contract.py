from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256

RIGHTS_STATES = {
    "OPEN_REUSE",
    "PUBLIC_ACCESS_LIMITED_REUSE",
    "PERMISSION_REQUIRED",
    "UNKNOWN",
}
LAYERS = {"metadata", "transcription", "translation", "image"}

@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    stable_id: str
    source_url: str
    rights: dict[str, str]
    raw_transcription: str | None = None
    translation: str | None = None
    metadata: dict = field(default_factory=dict)

def checksum_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()

def validate_rights(record: SourceRecord) -> None:
    for layer, state in record.rights.items():
        if layer not in LAYERS:
            raise ValueError(f"unknown layer {layer}")
        if state not in RIGHTS_STATES:
            raise ValueError(f"unknown rights state {state}")

def can_copy_layer(record: SourceRecord, layer: str) -> bool:
    validate_rights(record)
    state = record.rights.get(layer, "UNKNOWN")
    return state == "OPEN_REUSE"

def canonical_reference(record: SourceRecord) -> dict:
    validate_rights(record)
    out = {
        "source_id": record.source_id,
        "stable_id": record.stable_id,
        "source_url": record.source_url,
        "rights": dict(record.rights),
        "metadata": dict(record.metadata),
    }
    if record.raw_transcription is not None:
        out["transcription_checksum"] = checksum_text(record.raw_transcription)
        if can_copy_layer(record, "transcription"):
            out["diplomatic_transcription"] = record.raw_transcription
        else:
            out["diplomatic_transcription"] = None
            out["transcription_reference_only"] = True
    if record.translation is not None:
        if can_copy_layer(record, "translation"):
            out["translation"] = record.translation
        else:
            out["translation"] = None
            out["translation_reference_only"] = True
    return out
