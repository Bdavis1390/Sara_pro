import tempfile
from pathlib import Path
import unittest

from research.ws_qbench_mgraph_v01.code_s1_ingest_v10 import (
    CodeS1IngestError,
    EXPECTED_FILES,
    candidate_zero_semantics_questions,
    inventory_code_s1,
    require_reviewed_hash_lock,
    scan_matlab_text,
)


class TestCodeS1IngestV10(unittest.TestCase):
    def test_marker_scan(self):
        text = "x=factorial(n); y=laguerreL(n,a,z); w=prod(v); if w~=0, r=randperm(10); end"
        row = scan_matlab_text(text)
        self.assertEqual(row["factorial"], 1)
        self.assertEqual(row["laguerre"], 1)
        self.assertEqual(row["prod"], 1)
        self.assertEqual(row["exact_zero_test"], 1)
        self.assertEqual(row["randperm"], 1)

    def test_missing_expected_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CodeS1IngestError):
                inventory_code_s1(tmp)

    def test_inventory_and_hash_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contents = {
                EXPECTED_FILES[0]: "x=factorial(5);\n",
                EXPECTED_FILES[1]: "idx=randperm(201,10); w=prod(v); if w~=0; end\n",
                EXPECTED_FILES[2]: "plot(x,y);\n",
            }
            for name, body in contents.items():
                (root / name).write_text(body, encoding="utf-8")
            manifest = inventory_code_s1(root)
            self.assertFalse(manifest["execution_performed"])
            self.assertTrue(manifest["review_required"])
            locks = {row["filename"]: row["sha256"] for row in manifest["files"]}
            require_reviewed_hash_lock(manifest, locks)

    def test_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in EXPECTED_FILES:
                (root / name).write_text(name, encoding="utf-8")
            manifest = inventory_code_s1(root)
            bad = {name: "0" * 64 for name in EXPECTED_FILES}
            with self.assertRaises(CodeS1IngestError):
                require_reviewed_hash_lock(manifest, bad)

    def test_questions_are_source_marker_driven(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / EXPECTED_FILES[0]).write_text("a=laguerreL(2,3,x);\n", encoding="utf-8")
            (root / EXPECTED_FILES[1]).write_text("w=prod(v); if w==0; end\n", encoding="utf-8")
            (root / EXPECTED_FILES[2]).write_text("plot(x,y);\n", encoding="utf-8")
            questions = candidate_zero_semantics_questions(inventory_code_s1(root))
            self.assertTrue(any("Laguerre" in q for q in questions))
            self.assertTrue(any("multiplication order" in q for q in questions))
            self.assertTrue(any("zero/nonzero" in q for q in questions))


if __name__ == "__main__":
    unittest.main()
