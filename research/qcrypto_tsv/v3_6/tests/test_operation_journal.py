from __future__ import annotations

import os
import pathlib
import tempfile
import unittest

from worldshepherd_qcrypto_kms.operation_journal import FileOperationJournal, OperationJournalError


class OperationJournalHardeningTests(unittest.TestCase):
    def test_permissions_are_private(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td) / "journal"
            j = FileOperationJournal(root)
            self.assertEqual(os.stat(j.root).st_mode & 0o777, 0o700)
            self.assertEqual(os.stat(j.root / ".journal.lock").st_mode & 0o777, 0o600)
            j.claim_for_sign("SAFE_op-1", {"a": "b"})
            self.assertEqual(os.stat(j.root / "SAFE_op-1.json").st_mode & 0o777, 0o600)

    def test_symlink_root_is_rejected(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td) / "target"
            target.mkdir()
            link = pathlib.Path(td) / "journal-link"
            os.symlink(target, link)
            with self.assertRaises(OperationJournalError):
                FileOperationJournal(link)


if __name__ == "__main__":
    unittest.main()
