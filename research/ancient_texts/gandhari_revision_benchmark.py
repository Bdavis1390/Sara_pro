from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class RevisionClass(str, Enum):
    ORTHOGRAPHIC_NONMATERIAL = "ORTHOGRAPHIC_NONMATERIAL"
    SIGN_READING = "SIGN_READING"
    SEGMENTATION = "SEGMENTATION"
    LEXICAL = "LEXICAL"
    MORPHOLOGICAL = "MORPHOLOGICAL"
    SYNTACTIC = "SYNTACTIC"
    NAMED_ENTITY = "NAMED_ENTITY"
    RESTORATION = "RESTORATION"
    OMISSION_ADDITION = "OMISSION_ADDITION"
    ORDER = "ORDER"
    INTERPRETATION_ONLY = "INTERPRETATION_ONLY"
    UNRESOLVED = "UNRESOLVED"

@dataclass(frozen=True)
class RevisionCase:
    case_id: str
    old_reading: str
    current_reading: str
    revision_class: RevisionClass
    translation_dependency_found: bool | None = None
    dependent_translation_ref: str | None = None
    current_interpretation_ref: str | None = None
    editor_note_ref: str | None = None
    confidence: float | None = None

    def materiality(self) -> str:
        if self.revision_class == RevisionClass.ORTHOGRAPHIC_NONMATERIAL:
            return "NONMATERIAL"
        if self.revision_class in {
            RevisionClass.LEXICAL,
            RevisionClass.MORPHOLOGICAL,
            RevisionClass.SYNTACTIC,
            RevisionClass.NAMED_ENTITY,
            RevisionClass.RESTORATION,
            RevisionClass.OMISSION_ADDITION,
            RevisionClass.ORDER,
        }:
            return "POTENTIALLY_MATERIAL"
        return "REVIEW_REQUIRED"

    def translation_action(self) -> str:
        materiality = self.materiality()
        if materiality == "NONMATERIAL":
            return "NO_REAUDIT_REQUIRED_ON_THIS_CHANGE"
        if self.translation_dependency_found is False:
            return "NO_DEPENDENT_TRANSLATION_IDENTIFIED"
        if self.translation_dependency_found is True:
            return "REAUDIT_DEPENDENT_TRANSLATION"
        return "DEPENDENCY_SEARCH_REQUIRED"

def adjudication_target(case: RevisionCase) -> str:
    if case.current_interpretation_ref and case.dependent_translation_ref:
        return "FULL_TRANSLATION_LINEAGE_ADJUDICATION"
    if case.editor_note_ref:
        return "READING_MATERIALITY_ADJUDICATION"
    return "SOURCE_CONTEXT_REQUIRED"

def survival_label(
    old_translation_semantics: str | None,
    current_translation_semantics: str | None,
) -> str:
    if not old_translation_semantics or not current_translation_semantics:
        return "UNRESOLVED"
    if old_translation_semantics.strip().lower() == current_translation_semantics.strip().lower():
        return "SEMANTICS_SURVIVE_REVISION"
    return "SEMANTICS_CHANGED_AFTER_REVISION"
