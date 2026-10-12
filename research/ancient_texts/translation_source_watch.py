from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class WatchSeverity(str, Enum):
    INFO = "INFO"
    REVIEW = "REVIEW"
    REAUDIT = "REAUDIT"
    BLOCK = "BLOCK"

@dataclass(frozen=True)
class WatchSignal:
    source: str
    record_id: str
    signal: str
    severity: WatchSeverity
    rationale: str

def damos_note_signals(record_id: str, notes: str) -> list[WatchSignal]:
    out: list[WatchSignal] = []
    checks = [
        ("JOIN€", WatchSeverity.REAUDIT, "New join can change segmentation/context."),
        ("READ€", WatchSeverity.REAUDIT, "New/different reading can change lexical analysis or translation."),
        ("CORRECTION€", WatchSeverity.REAUDIT, "Published correction can supersede a dependent translation."),
        ("æ1", WatchSeverity.REVIEW, "Alternative reading exists."),
        ("æ2", WatchSeverity.REVIEW, "Alternative reading exists."),
        ("Qþ", WatchSeverity.REVIEW, "Open attribution/reading context noted."),
    ]
    for token, severity, rationale in checks:
        if token in notes:
            out.append(WatchSignal("DAMOS", record_id, token, severity, rationale))
    return out

def tla_editorial_state_signal(record_id: str, editorial_state: str) -> WatchSignal:
    normalized = editorial_state.strip().lower()
    if "verification pending" in normalized:
        return WatchSignal(
            "TLA", record_id, editorial_state, WatchSeverity.REVIEW,
            "Lemma/editorial state is not yet verified; do not promote as uniquely settled."
        )
    if "verified" in normalized:
        return WatchSignal(
            "TLA", record_id, editorial_state, WatchSeverity.INFO,
            "Editorial state reports verification; retain edition/version provenance."
        )
    return WatchSignal(
        "TLA", record_id, editorial_state, WatchSeverity.REVIEW,
        "Unknown editorial state requires explicit review."
    )

def gandhari_revision_signal(
    record_id: str,
    accepted_reading_changed: bool,
    interpretation_changed: bool,
) -> list[WatchSignal]:
    out: list[WatchSignal] = []
    if accepted_reading_changed:
        out.append(WatchSignal(
            "GANDHARI", record_id, "ACCEPTED_READING_CHANGED",
            WatchSeverity.REAUDIT,
            "Accepted text changed; dependent translation/interpretation must be revalidated."
        ))
    if interpretation_changed:
        out.append(WatchSignal(
            "GANDHARI", record_id, "INTERPRETATION_CHANGED",
            WatchSeverity.REVIEW,
            "Historical/current interpretation differs; preserve both with provenance."
        ))
    return out

def undeciphered_translation_signal(
    source: str,
    record_id: str,
    running_translation_present: bool,
    validated_decipherment: bool,
) -> WatchSignal:
    if running_translation_present and not validated_decipherment:
        return WatchSignal(
            source, record_id, "UNVALIDATED_RUNNING_TRANSLATION",
            WatchSeverity.BLOCK,
            "Undeciphered script cannot receive running semantic translation without validated decipherment."
        )
    return WatchSignal(
        source, record_id, "NO_BLOCKING_UNDECIPHERED_TRANSLATION",
        WatchSeverity.INFO,
        "No prohibited running translation detected."
    )
