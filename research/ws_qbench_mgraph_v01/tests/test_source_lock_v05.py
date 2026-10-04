import copy
import json
import unittest
from pathlib import Path

from research.ws_qbench_mgraph_v01.source_lock_v05 import (
    SourceLockError,
    authorize_exact_figure_reproduction,
    compute_lock_digest,
    load_source_lock,
    unresolved_exact_reproduction_gaps,
    validate_source_lock,
)


HERE = Path(__file__).resolve().parents[1]
LOCK_PATH = HERE / "SOURCE_LOCK_V0_5.json"


class SourceLockV05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))

    def _redigest(self, payload):
        payload["lock_digest_sha256"] = compute_lock_digest(payload)
        return payload

    def test_repository_lock_validates(self):
        validate_source_lock(self.lock)
        loaded = load_source_lock(LOCK_PATH)
        self.assertEqual(loaded["schema"], "ws-qbench-mgraph/source-lock-v0.5")

    def test_all_four_exact_reproduction_gaps_remain_blocking(self):
        self.assertEqual(
            unresolved_exact_reproduction_gaps(self.lock),
            [
                "G1_effective_zero_connected_loop",
                "G2_figure4ef_hamiltonian_normalization",
                "G3_random_subgraph_duplicate_policy",
                "G4_author_code",
            ],
        )
        with self.assertRaises(SourceLockError):
            authorize_exact_figure_reproduction(self.lock)

    def test_digest_detects_unreviewed_mutation(self):
        altered = copy.deepcopy(self.lock)
        altered["gaps"]["G2_figure4ef_hamiltonian_normalization"]["status"] = "locked"
        with self.assertRaises(SourceLockError):
            validate_source_lock(altered)

    def test_claim_policy_fails_closed_if_exact_reproduction_enabled_early(self):
        altered = copy.deepcopy(self.lock)
        altered["claims_policy"]["exact_figure_reproduction_allowed"] = True
        self._redigest(altered)
        with self.assertRaises(SourceLockError):
            validate_source_lock(altered)

    def test_hardware_inference_is_rejected(self):
        altered = copy.deepcopy(self.lock)
        altered["claims_policy"]["hardware_inference_allowed"] = True
        self._redigest(altered)
        with self.assertRaises(SourceLockError):
            validate_source_lock(altered)

    def test_exact_reproduction_unlocks_only_when_all_gaps_locked(self):
        altered = copy.deepcopy(self.lock)
        for gap in altered["gaps"].values():
            gap["status"] = "locked"
        altered["claims_policy"]["exact_figure_reproduction_allowed"] = True
        self._redigest(altered)
        validate_source_lock(altered)
        authorize_exact_figure_reproduction(altered)


if __name__ == "__main__":
    unittest.main()
