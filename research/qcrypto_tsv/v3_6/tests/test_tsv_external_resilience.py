import copy
import json
import unittest
from pathlib import Path
from worldshepherd_qcrypto_kms.tsv.external_resilience import validate_external_resilience_bundle

ROOT=Path(__file__).resolve().parents[1]
BUNDLE=json.loads((ROOT/'evidence'/'TSV_EXTERNAL_RESILIENCE_BUNDLE_V3_6.json').read_text())
PARENT='9b41b15e58898fe9f8fa836b258b13e93e860d20ea2c19e76693bfb3e3948653'
CORE='b6920cfa2fb8609991b623ceabe61b8b1c0d432cb293a13082fba8eab1977dfa'

class TestExternalResilience(unittest.TestCase):
    def test_actual_bundle_allows(self):
        r=validate_external_resilience_bundle(BUNDLE,expected_parent_v3_5_sha256=PARENT,expected_resilience_core_sha256=CORE)
        self.assertEqual(r.decision,'ALLOW',r.to_dict()); self.assertEqual(r.case_count,10)

    def test_wrong_expected_parent_denies(self):
        r=validate_external_resilience_bundle(BUNDLE,expected_parent_v3_5_sha256='0'*64,expected_resilience_core_sha256=CORE)
        self.assertEqual(r.decision,'DENY'); self.assertIn('PARENT_V35_MISMATCH',r.errors)

    def test_wrong_core_denies(self):
        r=validate_external_resilience_bundle(BUNDLE,expected_parent_v3_5_sha256=PARENT,expected_resilience_core_sha256='0'*64)
        self.assertEqual(r.decision,'DENY'); self.assertIn('RESILIENCE_CORE_MISMATCH',r.errors)

    def test_case_decision_mutation_denies(self):
        b=copy.deepcopy(BUNDLE); b['cases'][0]['decision']='DENY'
        r=validate_external_resilience_bundle(b,expected_parent_v3_5_sha256=PARENT,expected_resilience_core_sha256=CORE)
        self.assertEqual(r.decision,'DENY')
        self.assertTrue(any(x.startswith('CASE_DECISION_MISMATCH') for x in r.errors))

    def test_bundle_hash_mutation_denies(self):
        b=copy.deepcopy(BUNDLE); b['durable_state_sha256']='0'*64
        r=validate_external_resilience_bundle(b,expected_parent_v3_5_sha256=PARENT,expected_resilience_core_sha256=CORE)
        self.assertEqual(r.decision,'DENY'); self.assertIn('BUNDLE_HASH_MISMATCH',r.errors)

    def test_negative_claim_promotion_denies(self):
        b=copy.deepcopy(BUNDLE); b['negative_claims']['licensed_market_data_used']=True
        r=validate_external_resilience_bundle(b,expected_parent_v3_5_sha256=PARENT,expected_resilience_core_sha256=CORE)
        self.assertEqual(r.decision,'DENY'); self.assertIn('NEGATIVE_CLAIM_NOT_FALSE:licensed_market_data_used',r.errors)
