import hashlib
import unittest

from ws_cae.continuity_lineage import assess_lineage
from ws_cae.continuity_transition import ContinuityTransition


def cid(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def transition(subject: str, old: str, new: str):
    return ContinuityTransition(subject, old, new, "ALGORITHM_MIGRATION", "2026-09-13T23:10:00Z")


class ContinuityLineageTests(unittest.TestCase):
    def test_linear_lineage_passes(self):
        a, b, c = cid("a"), cid("b"), cid("c")
        result = assess_lineage((transition("asset", a, b), transition("asset", b, c)), genesis_content_id=a)
        self.assertTrue(result.valid)
        self.assertEqual(result.tip_content_ids, (c,))
        self.assertEqual(result.fork_points, tuple())

    def test_fork_is_flagged(self):
        a, b, c = cid("a"), cid("b"), cid("c")
        result = assess_lineage((transition("asset", a, b), transition("asset", a, c)), genesis_content_id=a)
        self.assertFalse(result.valid)
        self.assertEqual(result.fork_points, (a,))

    def test_unreachable_state_is_flagged(self):
        a, b, x, y = cid("a"), cid("b"), cid("x"), cid("y")
        result = assess_lineage((transition("asset", a, b), transition("asset", x, y)), genesis_content_id=a)
        self.assertFalse(result.valid)
        self.assertTrue(any("not reachable" in issue for issue in result.issues))

    def test_multiple_subjects_are_rejected(self):
        a, b, c = cid("a"), cid("b"), cid("c")
        result = assess_lineage((transition("one", a, b), transition("two", b, c)), genesis_content_id=a)
        self.assertFalse(result.valid)
        self.assertTrue(any("more than one subject" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
