from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

HDTN_REPOSITORY = "https://github.com/nasa/HDTN.git"
HDTN_PINNED_COMMIT = "7fbe90cdbe3c8c737efaacb5985f881f95fc7d2a"


@dataclass(frozen=True)
class HdtnContact:
    contact: int
    source: int
    dest: int
    startTime: int
    endTime: int
    rateBitsPerSec: int
    owlt: int

    def validate(self) -> None:
        if self.contact < 0:
            raise ValueError("contact id must be non-negative")
        if self.source <= 0 or self.dest <= 0 or self.source == self.dest:
            raise ValueError("source and destination must be distinct positive node ids")
        if self.startTime < 0 or self.endTime <= self.startTime:
            raise ValueError("contact time window is invalid")
        if self.rateBitsPerSec <= 0:
            raise ValueError("contact rate must be positive")
        if self.owlt < 0:
            raise ValueError("owlt must be non-negative")


def validate_contacts(contacts: Iterable[HdtnContact]) -> list[HdtnContact]:
    materialized = list(contacts)
    seen_ids: set[int] = set()
    for item in materialized:
        item.validate()
        if item.contact in seen_ids:
            raise ValueError(f"duplicate contact id: {item.contact}")
        seen_ids.add(item.contact)
    return materialized


def to_hdtn_contact_plan(contacts: Iterable[HdtnContact]) -> dict[str, object]:
    checked = validate_contacts(contacts)
    return {"contacts": [asdict(item) for item in checked]}


def write_hdtn_contact_plan(path: str | Path, contacts: Iterable[HdtnContact]) -> str:
    payload = to_hdtn_contact_plan(contacts)
    encoded = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    Path(path).write_text(encoded, encoding="utf-8")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def reference_cislunar_contacts() -> list[HdtnContact]:
    """Compile a disruption-rich A->B->C schedule into NASA HDTN contact-plan form.

    Node 1 is the lunar asset, node 2 is the cislunar relay, and node 3 is the
    Earth gateway.  The windows deliberately contain outages so HDTN storage and
    routing can be exercised.  Rates are test parameters, not hardware claims.
    HDTN's public sample contact plan uses integer-second OWLT fields, so v0.2
    uses 1 second per hop rather than claiming a precision lunar ephemeris model.
    """
    windows_ab = [
        (0, 180, 622_000_000),
        (300, 420, 80_000_000),
        (510, 900, 622_000_000),
        (910, 1250, 622_000_000),
        (1340, 5000, 622_000_000),
    ]
    windows_bc = [
        (0, 180, 622_000_000),
        (300, 700, 622_000_000),
        (790, 900, 100_000_000),
        (910, 1250, 622_000_000),
        (1340, 5000, 622_000_000),
    ]
    contacts: list[HdtnContact] = []
    contact_id = 0
    for start, end, rate in windows_ab:
        contacts.append(HdtnContact(contact_id, 1, 2, start, end, rate, 1))
        contact_id += 1
    for start, end, rate in windows_bc:
        contacts.append(HdtnContact(contact_id, 2, 3, start, end, rate, 1))
        contact_id += 1
    return contacts


def upstream_manifest() -> dict[str, str]:
    return {
        "repository": HDTN_REPOSITORY,
        "commit": HDTN_PINNED_COMMIT,
        "integration": "WS-CISNET-HDTN-v0.2",
    }
