from __future__ import annotations
from dataclasses import dataclass, field
import xml.etree.ElementTree as ET

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}

@dataclass(frozen=True)
class WitnessReading:
    apparatus_id: str | None
    lemma: str | None
    reading: str
    witnesses: tuple[str, ...]
    responsibility: str | None = None
    certainty: str | None = None
    reading_type: str | None = None

def _text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    value = "".join(el.itertext()).strip()
    return value or None

def parse_tei_apparatus(xml_text: str) -> list[WitnessReading]:
    root = ET.fromstring(xml_text)
    out: list[WitnessReading] = []
    for app in root.findall(".//tei:app", TEI_NS):
        app_id = app.attrib.get("{http://www.w3.org/XML/1998/namespace}id")
        lem = _text(app.find("tei:lem", TEI_NS))
        for rdg in app.findall("tei:rdg", TEI_NS):
            wit = tuple(
                item.lstrip("#")
                for item in rdg.attrib.get("wit", "").split()
                if item
            )
            out.append(WitnessReading(
                apparatus_id=app_id,
                lemma=lem,
                reading=_text(rdg) or "",
                witnesses=wit,
                responsibility=rdg.attrib.get("resp"),
                certainty=rdg.attrib.get("cert"),
                reading_type=rdg.attrib.get("type"),
            ))
    return out

def apparatus_requires_translation_review(readings: list[WitnessReading]) -> bool:
    distinct = {r.reading for r in readings if r.reading}
    uncertain = any(r.certainty not in (None, "high") for r in readings)
    return len(distinct) > 1 or uncertain
