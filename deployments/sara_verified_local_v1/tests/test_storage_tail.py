from __future__ import annotations

import json

from worldshepherd_sara.limits import MAX_AUDIT_LINE_BYTES
from worldshepherd_sara.storage import DurableStore


def _write_raw(store: DurableStore, payload: bytes) -> None:
    store.audit_path.write_bytes(payload)
    store.audit_path.chmod(0o600)


def _line(sequence: int) -> bytes:
    return json.dumps(
        {"event": "fixture", "sequence": sequence},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def test_bounded_tail_returns_newest_records_in_chronological_order(tmp_path):
    store = DurableStore(tmp_path / "data")
    _write_raw(store, b"\n".join(_line(i) for i in range(6)) + b"\n")

    records = store.read_audit(3)

    assert [record["sequence"] for record in records] == [3, 4, 5]


def test_bounded_tail_supports_final_line_without_terminal_newline(tmp_path):
    store = DurableStore(tmp_path / "data")
    _write_raw(store, _line(1) + b"\n" + _line(2))

    assert store.read_audit(1) == [{"event": "fixture", "sequence": 2}]


def test_bounded_tail_preserves_empty_line_corruption_semantics(tmp_path):
    store = DurableStore(tmp_path / "data")
    _write_raw(store, _line(1) + b"\n\n")

    assert store.read_audit(2) == [
        {"event": "fixture", "sequence": 1},
        {"event": "audit_corruption_detected", "reason": "invalid_line"},
    ]


def test_single_empty_jsonl_record_is_still_labeled_invalid(tmp_path):
    store = DurableStore(tmp_path / "data")
    _write_raw(store, b"\n")

    assert store.read_audit(1) == [
        {"event": "audit_corruption_detected", "reason": "invalid_line"}
    ]


def test_selected_overlong_tail_line_is_labeled_without_unbounded_buffer(tmp_path):
    store = DurableStore(tmp_path / "data")
    _write_raw(
        store,
        _line(1) + b"\n" + (b"x" * (MAX_AUDIT_LINE_BYTES + 257)) + b"\n",
    )

    assert store.read_audit(1) == [
        {"event": "audit_corruption_detected", "reason": "line_too_long"}
    ]
