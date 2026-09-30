from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class ReauditState(str, Enum):
    CONFIRMED_STALE = "CONFIRMED_STALE"
    RESOLVED_CURRENT_ON_AUDITED_CHANGE = "RESOLVED_CURRENT_ON_AUDITED_CHANGE"
    MATERIAL_CHANGE_TRANSLATION_UNRESOLVED = "MATERIAL_CHANGE_TRANSLATION_UNRESOLVED"
    NONMATERIAL_CHANGE = "NONMATERIAL_CHANGE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

@dataclass(frozen=True)
class ChangedReading:
    record_id: str
    current_reading: str
    previous_reading: str | None
    translated_form: str | None
    semantic_role: str
    material_to_translation: bool = True

def normalized(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(ch.lower() for ch in value if ch.isalnum())

def classify_changed_reading(change: ChangedReading) -> ReauditState:
    if not change.material_to_translation:
        return ReauditState.NONMATERIAL_CHANGE

    cur = normalized(change.current_reading)
    prev = normalized(change.previous_reading)
    tr = normalized(change.translated_form)

    if not tr:
        return ReauditState.MANUAL_REVIEW_REQUIRED

    if cur and tr and (cur == tr or cur in tr or tr in cur):
        return ReauditState.RESOLVED_CURRENT_ON_AUDITED_CHANGE

    if prev and tr and (prev == tr or prev in tr or tr in prev):
        return ReauditState.CONFIRMED_STALE

    return ReauditState.MATERIAL_CHANGE_TRANSLATION_UNRESOLVED

def named_entity_change(
    record_id: str,
    current_name: str,
    previous_name: str | None,
    translated_name: str | None,
) -> ChangedReading:
    return ChangedReading(
        record_id=record_id,
        current_reading=current_name,
        previous_reading=previous_name,
        translated_form=translated_name,
        semantic_role="NAMED_ENTITY",
        material_to_translation=True,
    )
