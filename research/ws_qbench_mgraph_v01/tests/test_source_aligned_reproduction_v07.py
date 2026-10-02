import json
from pathlib import Path
import unittest

from research.ws_qbench_mgraph_v01.source_aligned_reproduction_v07 import (
    AuthorLockedParameters,
    classify_author_loop_product,
)
from research.ws_qbench_mgraph_v01.source_lock_v07 import (
    SourceLockError,
    authorize_exact_figure_reproduction,
    compute_lock_digest,
    load_source_lock,
)


ROOT = Path(__file__).resolve().parents[1]


class TestAuthorAlignedReproductionV07(unittest.TestCase):
    def test_author_locked_defaults(self):
        row = AuthorLockedParameters()
        self.assertEqual(row.nmax, 200)
        self.assertEqual(row.realizations, 20_000)
        self.assertEqual(row.q_values, tuple(range(2, 11)) + (30, 50))
        self.assertEqual(row.h_perp, 0.5)
        self.assertEqual(row.h_parallel, 0.0)
        self.assertEqual(row.eigenstates, 30)

    def test_exact_zero_is_disconnected(self):
        self.assertEqual(classify_author_loop_product(0.0 + 0.0j), (False, None))

    def test_phase_zero_is_trivial(self):
        self.assertEqual(classify_author_loop_product(1.0 + 0.0j), (True, "trivial"))

    def test_phase_pi_is_nontrivial(self):
        self.assertEqual(classify_author_loop_product(-1.0 + 0.0j), (True, "nontrivial"))

    def test_v07_lock_resolves_g1_to_g3_but_keeps_code_gate(self):
        payload = load_source_lock(ROOT / "SOURCE_LOCK_V0_7.json")
        self.assertEqual(payload["gaps"]["G1_effective_zero_connected_loop"]["status"], "locked")
        self.assertEqual(payload["gaps"]["G2_figure4ef_hamiltonian_normalization"]["status"], "locked")
        self.assertEqual(payload["gaps"]["G3_random_subgraph_duplicate_policy"]["status"], "locked")
        self.assertEqual(payload["gaps"]["G4_author_code"]["status"], "located_unverified")
        with self.assertRaises(SourceLockError):
            authorize_exact_figure_reproduction(payload)

    def test_lock_digest_rejects_unreviewed_change(self):
        payload = json.loads((ROOT / "SOURCE_LOCK_V0_7.json").read_text())
        payload["locked_conventions"]["Nmax"] = 199
        self.assertNotEqual(compute_lock_digest(payload), payload["lock_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
