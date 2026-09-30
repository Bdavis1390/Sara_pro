import json, unittest
from copy import deepcopy
from pathlib import Path
from worldshepherd_qcrypto_kms.tsv.external_adversarial import validate_external_adversarial_bundle

ROOT=Path(__file__).resolve().parents[1]
B=json.loads((ROOT/'evidence/TSV_EXTERNAL_ADVERSARIAL_BUNDLE_V3_5.json').read_text())
PARENT="806db617532dc8840dca3f39504efa4cd78f5b4312005d730e5a73e4b54fffd8"
CORE="4b4e1c85b80b8ad5b9326cbacec0a8754dcc80ec98cf2b2e7bc917cd921d8341"

class TestExternalAdversarial(unittest.TestCase):
    def v(self,b): return validate_external_adversarial_bundle(b,expected_parent_v3_4_sha256=PARENT,expected_control_core_sha256=CORE)
    def test_bundle_allows(self):
        r=self.v(B); self.assertEqual(r.decision,'ALLOW',r.errors); self.assertEqual(r.negative_case_count,11)
    def test_mutation_breaks_hash(self):
        b=deepcopy(B); b['pass_case']['request_id']=999
        self.assertIn('BUNDLE_HASH_MISMATCH',self.v(b).errors)
    def test_missing_case_fails(self):
        b=deepcopy(B); b['fail_cases']=b['fail_cases'][:-1]
        self.assertTrue(any(x.startswith('MISSING_FAIL_CASE:') for x in self.v(b).errors))
    def test_jwt_required(self):
        b=deepcopy(B); b['execution_target']['verify_jwt']=False
        self.assertIn('JWT_NOT_REQUIRED',self.v(b).errors)
    def test_parent_binding_required(self):
        r=validate_external_adversarial_bundle(B,expected_parent_v3_4_sha256='0'*64,expected_control_core_sha256=CORE)
        self.assertIn('PARENT_V34_MISMATCH',r.errors)
    def test_negative_claim_promotion_fails(self):
        b=deepcopy(B); b['negative_claims']['licensed_sip_feed_used']=True
        self.assertIn('NEGATIVE_CLAIM_NOT_FALSE:licensed_sip_feed_used',self.v(b).errors)
