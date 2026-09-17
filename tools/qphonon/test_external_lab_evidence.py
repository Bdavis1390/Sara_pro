from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_external_lab_evidence import validate


ROOT = Path(__file__).resolve().parents[2]
LEDGER = json.loads(
    (ROOT / "evidence" / "qphonon" / "external_lab_evidence_2026-09-17.json").read_text(encoding="utf-8")
)


class ExternalLabEvidenceTests(unittest.TestCase):
    def test_canonical_ledger_passes(self) -> None:
        self.assertEqual(validate(LEDGER), [])

    def test_cannot_promote_external_evidence_to_worldshepherd_controlled(self) -> None:
        data = copy.deepcopy(LEDGER)
        data["worldshepherd_controlled_experiment"] = True
        self.assertTrue(validate(data))

    def test_cannot_close_l3_with_publication_only(self) -> None:
        data = copy.deepcopy(LEDGER)
        data["closes_l3_partner_hardware_gate"] = True
        self.assertTrue(validate(data))

    def test_negative_claim_boundary_is_required(self) -> None:
        data = copy.deepcopy(LEDGER)
        data["records"][0]["does_not_support"] = []
        self.assertTrue(validate(data))


if __name__ == "__main__":
    unittest.main()
