from __future__ import annotations

import base64
import datetime as dt
import shutil
import tempfile
import unittest
from pathlib import Path

from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.bitcoin_tx import BitcoinTransaction, TxInput, TxOutput, encode_compact_size
from worldshepherd_qcrypto_kms.chain_context import ChainContextPolicy, validate_chain_context_report, verify_psbt_chain_context_with_core
from worldshepherd_qcrypto_kms.crypto_agility import AlgorithmFamily, CryptoAgilityPolicy
from worldshepherd_qcrypto_kms.emergency_state import EmergencyStateError, EmergencyStateLedger
from worldshepherd_qcrypto_kms.governance_plane import EmergencyMode
from worldshepherd_qcrypto_kms.migration_engine import MigrationBatchBinding
from worldshepherd_qcrypto_kms.migration_psbt import MigrationSpendInput, build_sweep_migration_psbt
from worldshepherd_qcrypto_kms.operation_journal import FileOperationJournal
from worldshepherd_qcrypto_kms.openssl_pq_provider import OpenSslPqAuthorizationProvider, generate_openssl_pq_private_key
from worldshepherd_qcrypto_kms.pq_quorum import CallablePqProviderAdapter, LatencyBudget, PqQuorumError, execute_and_verify_pq_quorum
from worldshepherd_qcrypto_kms.psbt_guard import audit_psbt
from worldshepherd_qcrypto_kms.release_policy import BitcoinReleaseIntent, RELEASE_ATTESTATION_CONTEXT

MAGIC=b"psbt\xff"
INPUT=bytes.fromhex("0014"+"33"*20)
PAYEE=bytes.fromhex("0014"+"11"*20)

def kv(key_type:int,value:bytes)->bytes:
    key=bytes([key_type])
    return encode_compact_size(len(key))+key+encode_compact_size(len(value))+value

def mp(*entries:bytes)->bytes: return b"".join(entries)+b"\x00"
def witness_utxo(value:int,script:bytes)->bytes: return value.to_bytes(8,"little")+encode_compact_size(len(script))+script

def make_psbt()->bytes:
    tx=BitcoinTransaction(version=2,inputs=(TxInput(prev_txid="77"*32,vout=0,script_sig=b"",sequence=0xFFFFFFFE),),outputs=(TxOutput(value_sat=99_000,script_pubkey=PAYEE),),locktime=0,segwit=False)
    return MAGIC+mp(kv(0x00,tx.serialize()))+mp(kv(0x01,witness_utxo(100_000,INPUT)))+mp()

def intent()->BitcoinReleaseIntent:
    return BitcoinReleaseIntent(network="SIGNET",unsigned_tx_sha256="11"*32,input_set_sha256="22"*32,output_set_sha256="33"*32,fee_sat=1000,policy_epoch="v3",signing_policy_sha256="44"*32,authorization_nonce="scope-parity-nonce-00001",expires_at="2099-01-01T00:00:00Z")

class FakeCore:
    network="SIGNET"
    def rpc(self, method, *params):
        if method=="getblockchaininfo":
            return {"chain":"signet","blocks":250,"bestblockhash":"aa"*32,"mediantime":int(dt.datetime(2026,9,18,18,tzinfo=dt.timezone.utc).timestamp()),"initialblockdownload":False}
        if method=="gettxout":
            return {"confirmations":12,"value":0.001,"scriptPubKey":{"hex":INPUT.hex()}}
        raise AssertionError(method)

class ScopeParityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("openssl"),"OpenSSL unavailable")
    def test_actual_openssl_fips204_and_fips205_authorization_and_durable_replay(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            generate_openssl_pq_private_key(td/"ml.pem",algorithm_id="ML-DSA-65")
            generate_openssl_pq_private_key(td/"slh.pem",algorithm_id="SLH-DSA-SHA2-128s")
            p1=OpenSslPqAuthorizationProvider(provider_id="LOCAL-ML",algorithm_id="ML-DSA-65",private_key_path=td/"ml.pem",operation_journal=FileOperationJournal(td/"j1"),software_private_key_authorized=True,fault_domain_id="LOCAL-OPENSSL")
            p2=OpenSslPqAuthorizationProvider(provider_id="LOCAL-SLH",algorithm_id="SLH-DSA-SHA2-128s",private_key_path=td/"slh.pem",operation_journal=FileOperationJournal(td/"j2"),software_private_key_authorized=True,fault_domain_id="LOCAL-OPENSSL")
            policy=CryptoAgilityPolicy(minimum_security_category=1,minimum_pq_attestations=2,required_pq_families=(AlgorithmFamily.LATTICE,AlgorithmFamily.HASH_BASED),minimum_provider_fault_domains=1,max_detached_signature_bytes=20_000)
            atts,report,timing=execute_and_verify_pq_quorum(intent=intent(),providers=(p1,p2),policy=policy,latency_budget=LatencyBudget(max_sign_ms_per_provider=5000,max_verify_ms_per_provider=5000,max_total_ms=15000))
            self.assertTrue(report["satisfied"])
            self.assertEqual([len(base64.urlsafe_b64decode(a.signature_b64url+"="*((-len(a.signature_b64url))%4))) for a in atts],[3309,7856])
            replay=p1.sign_release_intent(intent=intent(),context=RELEASE_ATTESTATION_CONTEXT)
            self.assertEqual(replay.signature_b64url,atts[0].signature_b64url)
            self.assertEqual(replay.operation_id,atts[0].operation_id)

    def test_fault_domain_separation_is_enforced(self):
        sig=b"x"*3309
        p1=CallablePqProviderAdapter(provider_id="p1",algorithm_id="ML-DSA-65",key_fingerprint_sha256="11"*32,signer=lambda m,c:(sig,"op1"),verifier=lambda m,c,s:s==sig,fault_domain_id="same-host")
        p2=CallablePqProviderAdapter(provider_id="p2",algorithm_id="ML-DSA-65",key_fingerprint_sha256="22"*32,signer=lambda m,c:(sig,"op2"),verifier=lambda m,c,s:s==sig,fault_domain_id="same-host")
        policy=CryptoAgilityPolicy(minimum_pq_attestations=2,required_pq_families=(AlgorithmFamily.LATTICE,),minimum_provider_fault_domains=2)
        with self.assertRaises(PqQuorumError):
            execute_and_verify_pq_quorum(intent=intent(),providers=(p1,p2),policy=policy,latency_budget=LatencyBudget())

    def test_migration_manifest_becomes_actual_bound_psbt(self):
        binding=MigrationBatchBinding(batch_id="b1",network="SIGNET",manifest_sha256="44"*32,outpoints=("77"*32+":0",),allowed_destination_script_types=("P2WPKH",),max_fee_sat=5000,reservation_nonce="migration-nonce-0001",expires_at="2099-01-01T00:00:00Z",generation=2)
        built=build_sweep_migration_psbt((MigrationSpendInput("77"*32,0,100_000,INPUT.hex()),),network="SIGNET",fee_sat=1000,binding=binding,destination_script_pubkey_hex=PAYEE.hex())
        self.assertEqual(built.output_value_sat,99_000)
        audit=audit_psbt(built.psbt,network="SIGNET",policy_state=CryptoPolicyState.ECDSA_ALLOWED,max_fee_sat=5000,reject_address_reuse=True,reject_rbf=True,reject_dust=True)
        self.assertTrue(audit.allowed)
        self.assertEqual(audit.fee_sat,1000)
        self.assertEqual(audit.metadata_exposure["input_outpoints"],["77"*32+":0"])

    def test_chain_context_checks_live_utxo_shape_and_hash_binding(self):
        report=verify_psbt_chain_context_with_core(make_psbt(),network="SIGNET",cli=FakeCore(),policy=ChainContextPolicy(minimum_confirmations=6,max_tip_age_seconds=7200),now=dt.datetime(2026,9,18,19,tzinfo=dt.timezone.utc))
        self.assertTrue(report["satisfied"])
        self.assertEqual(validate_chain_context_report(report,network="SIGNET",txid=report["txid"]),report["chain_context_sha256"])
        tampered=dict(report); tampered["height"]+=1
        with self.assertRaises(Exception): validate_chain_context_report(tampered,network="SIGNET",txid=report["txid"])

    def test_emergency_freeze_cannot_silently_reopen(self):
        with tempfile.TemporaryDirectory() as td:
            led=EmergencyStateLedger(Path(td)/"emergency.jsonl")
            led.transition(EmergencyMode.FREEZE,reason="Q-day response",expected_sequence=0)
            self.assertEqual(led.assert_current(EmergencyMode.FREEZE)["mode"],"FREEZE")
            with self.assertRaises(EmergencyStateError):
                led.transition(EmergencyMode.NORMAL,reason="attempt silent reopen",expected_sequence=1)
            led.transition(EmergencyMode.NORMAL,reason="authorized recovery",expected_sequence=1,recovery_authorization_sha256="55"*32)
            self.assertEqual(led.assert_current(EmergencyMode.NORMAL)["sequence"],2)

if __name__=="__main__": unittest.main()
