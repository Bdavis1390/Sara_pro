from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re

class TranslationTokenState(str, Enum):
    PLAIN = "PLAIN"
    SUPPLIED = "SUPPLIED"
    UNCERTAIN = "UNCERTAIN"
    BROKEN_OR_RESTORED = "BROKEN_OR_RESTORED"
    UNTRANSLATABLE = "UNTRANSLATABLE"

@dataclass(frozen=True)
class TranslationSpan:
    text: str
    state: TranslationTokenState

def translation_available(metadata: dict, text_id: str, language: str = "en") -> bool:
    formats = metadata.get("formats", {})
    return text_id in formats.get(f"tr-{language}", [])

def assert_translation_not_inferred_from_corpusjson(
    metadata: dict,
    text_id: str,
    corpusjson: dict,
) -> None:
    # ORACC corpusjson is transliteration/lemmatization/sign data;
    # translation availability is represented separately via formats/tr-*.
    if "translation" in corpusjson:
        return
    if translation_available(metadata, text_id):
        raise ValueError(
            "translation exists according to ORACC metadata but is not in corpusjson; "
            "fetch/parse the translation layer separately"
        )

def parse_oracc_translation_markup(text: str) -> list[TranslationSpan]:
    spans: list[TranslationSpan] = []
    cursor = 0
    pattern = re.compile(
        r"(@\?.+?\?@)|(\[[^\]]*\])|(\([^\)]*\))|(\.\.\.)",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        if match.start() > cursor:
            spans.append(TranslationSpan(text[cursor:match.start()], TranslationTokenState.PLAIN))
        token = match.group(0)
        if token.startswith("@?") and token.endswith("?@"):
            state = TranslationTokenState.UNCERTAIN
        elif token.startswith("["):
            state = TranslationTokenState.BROKEN_OR_RESTORED
        elif token.startswith("("):
            state = TranslationTokenState.SUPPLIED
        else:
            state = TranslationTokenState.UNTRANSLATABLE
        spans.append(TranslationSpan(token, state))
        cursor = match.end()
    if cursor < len(text):
        spans.append(TranslationSpan(text[cursor:], TranslationTokenState.PLAIN))
    return [s for s in spans if s.text]
