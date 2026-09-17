from __future__ import annotations

import json
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = json.loads(
    (ROOT / "evidence" / "qphonon" / "external_lab_evidence_2026-09-17.json").read_text(encoding="utf-8")
)


def record(evidence_id: str) -> dict:
    return next(item for item in LEDGER["records"] if item["evidence_id"] == evidence_id)


def finding(item: dict, quantity: str) -> dict:
    return next(value for value in item["measured_findings"] if value["quantity"] == quantity)


class ExternalLabPhysicsConsistencyTests(unittest.TestCase):
    def test_yale_q_frequency_and_reported_coherence_are_consistent(self) -> None:
        item = record("EXT-YALE-UHBAR-2026")
        f_hz = finding(item, "phonon_frequency")["value"] * 1e9
        q = finding(item, "maximum_Q")["value"]
        measured_ms = finding(item, "phonon_coherence_time")["value"]
        inferred_ms = q / (math.pi * f_hz) * 1e3
        self.assertLess(abs(inferred_ms - measured_ms) / measured_ms, 0.02)

    def test_yale_q_frequency_and_energy_decay_are_consistent(self) -> None:
        item = record("EXT-YALE-UHBAR-2026")
        f_hz = finding(item, "phonon_frequency")["value"] * 1e9
        q = finding(item, "maximum_Q")["value"]
        measured_ms = finding(item, "energy_decay_time")["value"]
        inferred_ms = q / (2.0 * math.pi * f_hz) * 1e3
        self.assertLess(abs(inferred_ms - measured_ms) / measured_ms, 0.02)

    def test_harvard_dressing_coherence_gain_exceeds_threefold(self) -> None:
        item = record("EXT-HARVARD-SIV-DRESSING-2026")
        bare = finding(item, "bare_T2_star")["value"]
        dressed = finding(item, "dressed_T2_star")["value"]
        self.assertGreater(dressed / bare, 3.0)


if __name__ == "__main__":
    unittest.main()
