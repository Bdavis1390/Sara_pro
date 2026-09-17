from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from validate_deployment import validate


ROOT = Path(__file__).resolve().parents[2]
PROFILE = json.loads((ROOT / "config" / "ws_qphonon_deployment_v0_3.json").read_text(encoding="utf-8"))


class DeploymentProfileTests(unittest.TestCase):
    def test_canonical_profile_passes(self) -> None:
        self.assertEqual(validate(PROFILE), [])

    def test_weakening_durable_replay_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["state_store"]["durable_replay_required"] = False
        self.assertTrue(validate(data))

    def test_adding_hardware_actuation_claim_fails(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["physical_boundary"]["hardware_actuation_endpoint_present"] = True
        self.assertTrue(validate(data))

    def test_generic_qpu_cannot_be_reclassified_as_phononic_evidence(self) -> None:
        data = copy.deepcopy(PROFILE)
        data["physical_boundary"]["generic_qpu_evidence_counts_as_phononic_evidence"] = True
        self.assertTrue(validate(data))


if __name__ == "__main__":
    unittest.main()
