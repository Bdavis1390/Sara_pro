from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = ROOT / "scripts" / "validate_spdx_pqc_fixtures.py"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

spec = importlib.util.spec_from_file_location("validate_spdx_pqc_fixtures", MODULE_PATH)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class SPDXPQCFixtureValidationTests(unittest.TestCase):
    def test_repository_fixtures_pass(self):
        self.assertEqual(validator.validate_directory(FIXTURES), [])

    def test_byte_to_bit_drift_is_rejected(self):
        data = validator.load_fixture(FIXTURES / "ml-kem.yaml")
        changed = deepcopy(data)
        changed["variants"][0]["lengths"]["publicKeyLength"]["normalizedValue"] += 1
        errors = validator.validate_fixture(changed, "mutated")
        self.assertTrue(any("sourceValue*8" in error for error in errors))

    def test_variant_omission_is_rejected(self):
        data = validator.load_fixture(FIXTURES / "ml-dsa.yaml")
        changed = deepcopy(data)
        changed["variants"].pop()
        errors = validator.validate_fixture(changed, "mutated")
        self.assertTrue(any("variant set mismatch" in error for error in errors))

    def test_claim_escalation_is_rejected(self):
        data = validator.load_fixture(FIXTURES / "slh-dsa.yaml")
        changed = deepcopy(data)
        changed["validation"]["implementationValidated"] = True
        errors = validator.validate_fixture(changed, "mutated")
        self.assertTrue(any("implementationValidated must remain false" in error for error in errors))

    def test_signing_mode_drift_is_rejected(self):
        data = validator.load_fixture(FIXTURES / "ml-dsa.yaml")
        changed = deepcopy(data)
        changed["variants"][0]["signingMode"] = ["deterministic"]
        errors = validator.validate_fixture(changed, "mutated")
        self.assertTrue(any("signingMode" in error for error in errors))

    def test_duplicate_variant_is_rejected(self):
        data = validator.load_fixture(FIXTURES / "ml-kem.yaml")
        changed = deepcopy(data)
        changed["variants"][1]["id"] = changed["variants"][0]["id"]
        errors = validator.validate_fixture(changed, "mutated")
        self.assertTrue(any("duplicate variant ids" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
