import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from worldshepherd_qcrypto_kms.tsv.durable_market_state import (
    DurableCursorStore, DurableCursorStoreError, apply_message_durably,
)
from worldshepherd_qcrypto_kms.tsv.market_data_adapter import MarketDataMessage

UTC=timezone.utc
NOW=datetime(2026,9,19,2,0,tzinfo=UTC)
REG={'PRIMARY_LISTING_EXCHANGE':{'sim-primary'}}

def msg(seq:int,payload:str|None=None,*,obs=None,eff=None):
    return MarketDataMessage('PRIMARY_LISTING_EXCHANGE','sim-primary','ABC',seq,'TRADING',eff or NOW-timedelta(seconds=2),obs or NOW-timedelta(seconds=1),payload or f'{seq:064x}',True,'v36')

class TestDurableMarketState(unittest.TestCase):
    def test_empty_store_has_revision_zero(self):
        with tempfile.TemporaryDirectory() as td:
            s=DurableCursorStore(Path(td)/'state.json').load()
            self.assertEqual(s.revision,0); self.assertEqual(len(s.state_sha256),64)

    def test_first_message_persists(self):
        with tempfile.TemporaryDirectory() as td:
            store=DurableCursorStore(Path(td)/'state.json')
            r=apply_message_durably(store,msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            self.assertEqual(r.decision,'ALLOW'); self.assertEqual(r.new_revision,1)
            self.assertTrue((Path(td)/'state.json').exists())

    def test_restart_continues_sequence(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'
            a=DurableCursorStore(path)
            self.assertEqual(apply_message_durably(a,msg(1),expected_symbol='ABC',now=NOW,source_registry=REG).decision,'ALLOW')
            b=DurableCursorStore(path)
            r=apply_message_durably(b,msg(2),expected_symbol='ABC',now=NOW,source_registry=REG)
            self.assertEqual(r.decision,'ALLOW'); self.assertEqual(r.new_revision,2)

    def test_restart_replay_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'
            apply_message_durably(DurableCursorStore(path),msg(2),expected_symbol='ABC',now=NOW,source_registry=REG)
            r=apply_message_durably(DurableCursorStore(path),msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            self.assertEqual(r.decision,'DENY'); self.assertIn('SEQUENCE_REPLAY_OR_REORDER',r.errors)

    def test_duplicate_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'; store=DurableCursorStore(path)
            a=apply_message_durably(store,msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            b=apply_message_durably(DurableCursorStore(path),msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            self.assertEqual(b.decision,'ALLOW_WITH_WARNINGS'); self.assertEqual(a.new_revision,b.new_revision)

    def test_equivocation_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'; store=DurableCursorStore(path)
            apply_message_durably(store,msg(1,'a'*64),expected_symbol='ABC',now=NOW,source_registry=REG)
            r=apply_message_durably(DurableCursorStore(path),msg(1,'b'*64),expected_symbol='ABC',now=NOW,source_registry=REG)
            self.assertEqual(r.decision,'DENY'); self.assertIn('SEQUENCE_EQUIVOCATION',r.errors)

    def test_gap_is_denied(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'; store=DurableCursorStore(path)
            apply_message_durably(store,msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            r=apply_message_durably(DurableCursorStore(path),msg(3),expected_symbol='ABC',now=NOW,source_registry=REG)
            self.assertEqual(r.decision,'DENY'); self.assertIn('SEQUENCE_GAP',r.errors)

    def test_tampered_store_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'; store=DurableCursorStore(path)
            apply_message_durably(store,msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            data=json.loads(path.read_text()); data['revision']=99; path.write_text(json.dumps(data))
            with self.assertRaises(DurableCursorStoreError): DurableCursorStore(path).load()

    def test_compare_and_swap_detects_concurrent_change(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.json'; store=DurableCursorStore(path)
            first=store.load()
            r=apply_message_durably(store,msg(1),expected_symbol='ABC',now=NOW,source_registry=REG)
            cursor=store.get_cursor(source_kind='PRIMARY_LISTING_EXCHANGE',source_id='sim-primary',symbol='ABC',session_id='v36')
            with self.assertRaises(DurableCursorStoreError): store.save_cursor(cursor,expected_state_sha256=first.state_sha256)
            self.assertEqual(r.new_revision,1)
