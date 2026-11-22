"""Independent negative tests for the deliberately self-reported bounded runner."""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bounded_execution import (
    ExecutionCustodyError,
    calculated_output,
    canonical,
    parse_object,
    receipt_digest,
    run_bounded,
    verify_receipt,
)


class BoundedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        for name in ("config.json", "input.json"):
            shutil.copy(ROOT / "examples/bounded_exec" / name, self.root / name)

    def run_one(self, run_id="a1"):
        return run_bounded(self.root, "config.json", "input.json", run_id)

    def test_recomputed_execution_record(self):
        receipt = self.run_one()
        report = verify_receipt(self.root, receipt)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["configuration_bytes_recomputed"])
        self.assertFalse(report["independent_witness_verified"])
        self.assertFalse(report["preexecution_freeze_verified"])
        self.assertEqual(
            parse_object((self.root / "runs/a1.output.json").read_bytes())["samples"],
            [-4, 2, 5, 14],
        )

    def test_configuration_actually_changes_computation(self):
        first = self.run_one("one")
        (self.root / "config.json").write_text('{"operation":"affine_v1","scale":2,"offset":0}\n')
        second = self.run_one("two")
        self.assertNotEqual(first["configuration"]["sha256"], second["configuration"]["sha256"])
        output = parse_object((self.root / "runs/two.output.json").read_bytes())
        self.assertEqual(output["samples"], [-4, 0, 2, 8])

    def test_tampered_configuration_rejected(self):
        receipt = self.run_one()
        (self.root / "config.json").write_text('{"operation":"affine_v1","scale":9,"offset":1}\n')
        with self.assertRaisesRegex(ExecutionCustodyError, "configuration bytes altered"):
            verify_receipt(self.root, receipt)

    def test_tampered_input_rejected(self):
        receipt = self.run_one()
        (self.root / "input.json").write_text('{"samples":[9]}\n')
        with self.assertRaisesRegex(ExecutionCustodyError, "input bytes altered"):
            verify_receipt(self.root, receipt)

    def test_tampered_output_rejected(self):
        receipt = self.run_one()
        (self.root / "runs/a1.output.json").write_text('{"samples":[1234]}\n')
        with self.assertRaisesRegex(ExecutionCustodyError, "output bytes altered"):
            verify_receipt(self.root, receipt)

    def test_rehashed_incorrect_output_rejected(self):
        receipt = self.run_one()
        wrong = b'{"samples":[1000],"schema":"WS-AFFINE-SYNTHETIC-OUTPUT-V1"}\n'
        (self.root / "runs/a1.output.json").write_bytes(wrong)
        import hashlib
        forged = copy.deepcopy(receipt)
        forged["output"]["sha256"] = hashlib.sha256(wrong).hexdigest()
        forged["receipt_sha256"] = receipt_digest({k:v for k,v in forged.items() if k != "receipt_sha256"})
        with self.assertRaisesRegex(ExecutionCustodyError, "synthetic output inconsistent"):
            verify_receipt(self.root, forged)

    def test_receipt_tamper_rejected(self):
        receipt = self.run_one()
        receipt["engine"] = "some-other-engine"
        with self.assertRaises(ExecutionCustodyError):
            verify_receipt(self.root, receipt)

    def test_independence_cannot_be_forged_even_with_new_digest(self):
        receipt = self.run_one()
        receipt["independent_witness"] = True
        receipt["receipt_sha256"] = receipt_digest({k:v for k,v in receipt.items() if k != "receipt_sha256"})
        with self.assertRaisesRegex(ExecutionCustodyError, "cannot claim external witnessing"):
            verify_receipt(self.root, receipt)

    def test_source_hash_substitution_rejected(self):
        receipt = self.run_one()
        receipt["source_sha256"] = "0"*64
        receipt["receipt_sha256"] = receipt_digest({k:v for k,v in receipt.items() if k != "receipt_sha256"})
        with self.assertRaisesRegex(ExecutionCustodyError, "verifier source"):
            verify_receipt(self.root, receipt)

    def test_invalid_run_id_blocks(self):
        with self.assertRaisesRegex(ExecutionCustodyError, "invalid run ID"):
            self.run_one("../a")

    def test_output_no_overwrite(self):
        self.run_one()
        with self.assertRaises(FileExistsError):
            self.run_one()

    def test_unsupported_operation_blocks(self):
        (self.root / "config.json").write_text('{"operation":"eval","scale":1,"offset":0}\n')
        with self.assertRaisesRegex(ExecutionCustodyError, "unsupported synthetic operation"):
            self.run_one()

    def test_boolean_coefficient_blocks(self):
        (self.root / "config.json").write_text('{"operation":"affine_v1","scale":true,"offset":0}\n')
        with self.assertRaisesRegex(ExecutionCustodyError, "invalid coefficients"):
            self.run_one()

    def test_symlinked_configuration_blocks(self):
        original = self.root / "config.json"
        original.unlink()
        original.symlink_to(ROOT / "examples/bounded_exec/config.json")
        with self.assertRaisesRegex(ExecutionCustodyError, "symlink"):
            self.run_one()

    def test_too_many_samples_blocks(self):
        (self.root / "input.json").write_text(json.dumps({"samples": list(range(129))}))
        with self.assertRaisesRegex(ExecutionCustodyError, "sample array"):
            self.run_one()

    def test_unsafe_output_reference_blocks(self):
        receipt = self.run_one()
        receipt["output"]["path"] = "config.json"
        receipt["output"]["sha256"] = receipt["configuration"]["sha256"]
        receipt["receipt_sha256"] = receipt_digest({k:v for k,v in receipt.items() if k != "receipt_sha256"})
        with self.assertRaises(ExecutionCustodyError):
            verify_receipt(self.root, receipt)

    def test_receipt_on_disk_matches_memory(self):
        receipt = self.run_one()
        persisted = parse_object((self.root / "runs/a1.receipt.json").read_bytes())
        self.assertEqual(receipt, persisted)
        self.assertEqual(verify_receipt(self.root, persisted)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
