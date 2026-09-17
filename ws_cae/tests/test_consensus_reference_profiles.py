import json
from pathlib import Path
import unittest

from ws_cae.consensus_cli import parse_profile
from ws_cae.consensus_continuity import assess_consensus


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FILES = (
    "bitcoin.consensus.json",
    "ethereum.consensus.json",
    "solana.consensus.json",
    "polkadot.consensus.json",
    "chia.consensus.json",
    "avalanche.consensus.json",
    "cometbft.consensus.json",
)


class ConsensusReferenceProfileTests(unittest.TestCase):
    def test_all_reference_profiles_are_parseable_and_valid(self):
        for filename in REFERENCE_FILES:
            with self.subTest(filename=filename):
                path = ROOT / "examples" / "consensus" / filename
                raw = json.loads(path.read_text(encoding="utf-8"))
                profile = parse_profile(raw)
                result = assess_consensus(profile)
                self.assertTrue(result.valid, msg=f"{filename}: {result.issues}")

    def test_reference_set_spans_multiple_consensus_families(self):
        families = set()
        for filename in REFERENCE_FILES:
            path = ROOT / "examples" / "consensus" / filename
            raw = json.loads(path.read_text(encoding="utf-8"))
            families.add(raw["consensus_family"])
        self.assertGreaterEqual(len(families), 6)

    def test_pq_state_never_promotes_unproven_reference_to_deployed(self):
        for filename in REFERENCE_FILES:
            with self.subTest(filename=filename):
                path = ROOT / "examples" / "consensus" / filename
                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertNotEqual(raw["consensus_pq_state"], "PQ_DEPLOYED")


if __name__ == "__main__":
    unittest.main()
