import json
import unittest
from pathlib import Path

from ws_cae.continuity_manifest import ContinuityManifest, DependencyRef, EvidenceRef, content_id
from ws_cae.continuity_transparency import inclusion_proof, root_hash


class ContinuityInteropVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = Path(__file__).resolve().parents[1] / "examples"
        cls.base = base
        cls.vectors = json.loads((base / "continuity_interop_vectors.json").read_text())

    def test_canonical_manifest_content_id(self):
        raw = json.loads((self.base / "continuity_manifest_reference.json").read_text())
        manifest = ContinuityManifest(
            subject_id=raw["subject_id"],
            subject_type=raw["subject_type"],
            version=raw["version"],
            as_of=raw["as_of"],
            authority_model=raw["authority_model"],
            implementation_maturity=raw["implementation_maturity"],
            protocol_commitment_state=raw["protocol_commitment_state"],
            pq_authorization_state=raw["pq_authorization_state"],
            consensus_pq_state=raw["consensus_pq_state"],
            crypto_agility_state=raw["crypto_agility_state"],
            recovery_state=raw["recovery_state"],
            dependencies=tuple(DependencyRef(**item) for item in raw["dependencies"]),
            evidence=tuple(EvidenceRef(**item) for item in raw["evidence"]),
        )
        self.assertEqual(content_id(manifest), self.vectors["canonical_manifest"]["expected_content_id"])

    def test_transparency_roots(self):
        ids = tuple(self.vectors["transparency"]["content_ids"])
        for size_text, expected in self.vectors["transparency"]["roots"].items():
            self.assertEqual(root_hash(ids[: int(size_text)]), expected)

    def test_inclusion_path(self):
        ids = tuple(self.vectors["transparency"]["content_ids"])
        vector = self.vectors["transparency"]["inclusion"]
        proof = inclusion_proof(ids[: vector["tree_size"]], vector["leaf_index"])
        self.assertEqual(list(proof.audit_path), vector["audit_path"])
        self.assertEqual(proof.root, self.vectors["transparency"]["roots"][str(vector["tree_size"])])


if __name__ == "__main__":
    unittest.main()
