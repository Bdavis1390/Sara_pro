from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from durable_state import DurableStateStore, ZERO_DIGEST


class DurableStateTests(unittest.TestCase):
    def test_replay_survives_store_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = DurableStateStore(path)
            self.assertTrue(store.consume_once("approval", "approval-1", "a" * 64))

            reopened = DurableStateStore(path)
            self.assertFalse(reopened.consume_once("approval", "approval-1", "a" * 64))

    def test_genesis_then_monotonic_event_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = DurableStateStore(path)

            ok, reason = store.commit_event(
                stream="lab-a",
                event_id="event-0",
                event_digest="a" * 64,
                sequence=0,
                previous_event_digest=ZERO_DIGEST,
            )
            self.assertTrue(ok, reason)

            reopened = DurableStateStore(path)
            state = reopened.get_stream("lab-a")
            self.assertIsNotNone(state)
            self.assertEqual(state.sequence, 0)
            self.assertEqual(state.event_digest, "a" * 64)

            ok, reason = reopened.commit_event(
                stream="lab-a",
                event_id="event-1",
                event_digest="b" * 64,
                sequence=1,
                previous_event_digest="a" * 64,
            )
            self.assertTrue(ok, reason)

    def test_sequence_skip_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableStateStore(Path(tmp) / "state.sqlite3")
            self.assertTrue(
                store.commit_event(
                    stream="lab-a",
                    event_id="event-0",
                    event_digest="a" * 64,
                    sequence=0,
                    previous_event_digest=ZERO_DIGEST,
                )[0]
            )
            ok, reason = store.commit_event(
                stream="lab-a",
                event_id="event-2",
                event_digest="c" * 64,
                sequence=2,
                previous_event_digest="a" * 64,
            )
            self.assertFalse(ok)
            self.assertEqual(reason, "EVENT_SEQUENCE_NOT_MONOTONIC")

    def test_chain_rollback_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableStateStore(Path(tmp) / "state.sqlite3")
            self.assertTrue(
                store.commit_event(
                    stream="lab-a",
                    event_id="event-0",
                    event_digest="a" * 64,
                    sequence=0,
                    previous_event_digest=ZERO_DIGEST,
                )[0]
            )
            ok, reason = store.commit_event(
                stream="lab-a",
                event_id="event-1",
                event_digest="b" * 64,
                sequence=1,
                previous_event_digest="f" * 64,
            )
            self.assertFalse(ok)
            self.assertEqual(reason, "EVENT_CHAIN_MISMATCH")

    def test_state_file_is_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            DurableStateStore(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
