import json
from copy import deepcopy
from pathlib import Path
import unittest

from worldshepherd_qcrypto_kms.tsv.external_execution import validate_external_tsv_execution_bundle

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = json.loads((ROOT / "evidence" / "TSV_EXTERNAL_EXECUTION_BUNDLE_V3_4.json").read_text())
REL = "fab44ddd5a1d46516f8d2b9fc759f4f23db7d811ab8a7d7a9b79da2d0400a25f"
MAN = "36af6e42fb78ab6e97a56678b87afc02ff71d4ea79d3d11a778eb03a31c9becc"


class TestTsvExternalExecution(unittest.TestCase):
    def validate(self, bundle):
        return validate_external_tsv_execution_bundle(
            bundle,
            expected_parent_release_sha256=REL,
            expected_parent_source_manifest_sha256=MAN,
        )

    def test_hosted_bundle_allows(self):
        r = self.validate(BUNDLE)
        self.assertEqual(r.decision, "ALLOW", r.errors)
        self.assertEqual(r.negative_case_count, 6)

    def test_bundle_mutation_fails_hash(self):
        b = deepcopy(BUNDLE)
        b["pass_case"]["aggregate_volume_share"] = 0.0002
        r = self.validate(b)
        self.assertEqual(r.decision, "DENY")
        self.assertIn("BUNDLE_HASH_MISMATCH", r.errors)

    def test_wrong_parent_fails(self):
        r = validate_external_tsv_execution_bundle(
            BUNDLE,
            expected_parent_release_sha256="0" * 64,
            expected_parent_source_manifest_sha256=MAN,
        )
        self.assertIn("PARENT_RELEASE_MISMATCH", r.errors)

    def test_missing_negative_case_fails_even_with_recomputed_hash_absent(self):
        b = deepcopy(BUNDLE)
        b["fail_cases"] = b["fail_cases"][:-1]
        r = self.validate(b)
        self.assertEqual(r.decision, "DENY")
        self.assertTrue(any(x.startswith("MISSING_FAIL_CASE:") for x in r.errors))

    def test_jwt_required(self):
        b = deepcopy(BUNDLE)
        b["execution_target"]["verify_jwt"] = False
        r = self.validate(b)
        self.assertIn("JWT_VERIFICATION_NOT_ENABLED", r.errors)

    def test_claim_boundary_cannot_be_promoted(self):
        b = deepcopy(BUNDLE)
        b["negative_claims"]["sec_approval_established"] = True
        r = self.validate(b)
        self.assertIn("NEGATIVE_CLAIM_NOT_FALSE:sec_approval_established", r.errors)


if __name__ == "__main__":
    unittest.main()
