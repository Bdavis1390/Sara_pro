from __future__ import annotations

import base64
import datetime as dt
import hashlib
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from worldshepherd_qcrypto_kms.approval_quorum import ApprovalStatement, sign_approval
from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState, UtxoRecord
from worldshepherd_qcrypto_kms.bitcoin_tx import BitcoinTransaction, TxInput, TxOutput, encode_compact_size
from worldshepherd_qcrypto_kms.control_plane import GovernedSigningPolicy, authorize_governed_signing, prepare_governed_signing
from worldshepherd_qcrypto_kms.crypto_agility import AlgorithmFamily, CryptoAgilityPolicy, evaluate_algorithm_set
from worldshepherd_qcrypto_kms.governance_plane import PrimePolicyProfile, SaraWorkflowJournal
from worldshepherd_qcrypto_kms.key_lifecycle import KeyLifecycleError, KeyRecord, KeyRegistry, KeyState
from worldshepherd_qcrypto_kms.migration_engine import MigrationEngineError, MigrationStateStore, build_migration_batches
from worldshepherd_qcrypto_kms.pq_quorum import CallablePqProviderAdapter, PqQuorumError
from worldshepherd_qcrypto_kms.policy_epoch import PolicyEpochError, QuantumPolicyLedger
from worldshepherd_qcrypto_kms.resource_budget import ResourceBudgetPolicy
from worldshepherd_qcrypto_kms.runtime_attestation import RuntimeAttestationStatement, sign_runtime_attestation, verify_runtime_attestation
from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest

MAGIC=b"psbt\xff"
INPUT=bytes.fromhex("0014"+"33"*20)
PAYEE=bytes.fromhex("0014"+"11"*20)

def kv(key_type:int,value:bytes,key_data:bytes=b"") -> bytes:
    key=encode_compact_size(key_type)+key_data
    return encode_compact_size(len(key))+key+encode_compact_size(len(value))+value

def mp(*entries:bytes)->bytes:
    return b"".join(entries)+b"\x00"

def witness_utxo(value_sat:int,script:bytes)->bytes:
    return value_sat.to_bytes(8,"little")+encode_compact_size(len(script))+script

def make_psbt(output_value:int=99_000)->bytes:
    tx=BitcoinTransaction(version=2,inputs=(TxInput(prev_txid="77"*32,vout=0,script_sig=b"",sequence=0xFFFFFFFE),),outputs=(TxOutput(value_sat=output_value,script_pubkey=PAYEE),),locktime=0,segwit=False)
    return MAGIC+mp(kv(0x00,tx.serialize()))+mp(kv(0x01,witness_utxo(100_000,INPUT)))+mp()


def approvals(intent_hash:str):
    k1=Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    k2=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
    a1=sign_approval(ApprovalStatement(intent_hash,"creator","CREATOR","2026-09-18T18:00:00Z","2099-09-19T18:00:00Z","creator-nonce-00000001"),k1)
    a2=sign_approval(ApprovalStatement(intent_hash,"operator","OPERATOR","2026-09-18T18:00:00Z","2099-09-19T18:00:00Z","operator-nonce-0000001"),k2)
    trusted={
        "creator":k1.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw),
        "operator":k2.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw),
    }
    return (a1,a2),trusted


class V3AgilityTests(unittest.TestCase):
    def test_two_family_policy_is_enforced(self):
        pol=CryptoAgilityPolicy(minimum_security_category=1,minimum_pq_attestations=2,required_pq_families=(AlgorithmFamily.LATTICE,AlgorithmFamily.HASH_BASED))
        self.assertFalse(evaluate_algorithm_set(("ML-DSA-65",),pol).satisfied)
        rep=evaluate_algorithm_set(("ML-DSA-65","SLH-DSA-SHA2-128s"),pol)
        self.assertTrue(rep.satisfied)
        self.assertEqual(rep.detached_signature_bytes,3309+7856)

    def test_key_registry_blocks_rollback_after_rotation(self):
        reg=KeyRegistry((
            KeyRecord("p","11"*32,"ML-DSA-65",1,KeyState.DEPRECATED,"2026-01-01T00:00:00Z",predecessor_fingerprint_sha256=None),
            KeyRecord("p","22"*32,"ML-DSA-65",2,KeyState.ACTIVE,"2026-02-01T00:00:00Z",predecessor_fingerprint_sha256="11"*32),
        ))
        with self.assertRaises(KeyLifecycleError):
            reg.authorize_key(provider_id="p",fingerprint_sha256="11"*32,algorithm_id="ML-DSA-65",allow_deprecated=True,now=dt.datetime(2026,9,18,tzinfo=dt.timezone.utc))
        self.assertTrue(reg.authorize_key(provider_id="p",fingerprint_sha256="22"*32,algorithm_id="ML-DSA-65",now=dt.datetime(2026,9,18,tzinfo=dt.timezone.utc))["authorized"])


class V3RuntimeTests(unittest.TestCase):

    def test_quantum_policy_ledger_prevents_policy_epoch_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            ledger=QuantumPolicyLedger(Path(td)/"policy.jsonl")
            first=ledger.transition(policy_state=CryptoPolicyState.ECDSA_ALLOWED,policy_epoch="epoch-1",effective_at="2026-09-18T18:00:00Z",reason="initial",expected_sequence=0)
            ledger.transition(policy_state=CryptoPolicyState.HYBRID_REQUIRED,policy_epoch="epoch-2",effective_at="2026-09-18T19:00:00Z",reason="raise protection",expected_sequence=1)
            with self.assertRaises(PolicyEpochError):
                ledger.transition(policy_state=CryptoPolicyState.ECDSA_ALLOWED,policy_epoch="epoch-3",effective_at="2026-09-18T20:00:00Z",reason="rollback",expected_sequence=2)
            with self.assertRaises(PolicyEpochError):
                ledger.assert_current(policy_state=CryptoPolicyState.ECDSA_ALLOWED,policy_epoch="epoch-1")
            self.assertTrue(ledger.assert_current(policy_state=CryptoPolicyState.HYBRID_REQUIRED,policy_epoch="epoch-2")["anchored"])

    def test_runtime_attestation_is_key_nonce_and_measurement_bound(self):
        key=Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        st=RuntimeAttestationStatement("verifier","provider","aa"*32,"NITRO_ENCLAVE_VERDICT","bb"*32,"runtime-nonce-0000001","2026-09-18T18:00:00Z","2099-09-19T18:00:00Z")
        signed=sign_runtime_attestation(st,key)
        rep=verify_runtime_attestation(signed,trusted_verifiers={"verifier":pub},allowed_measurements={"NITRO_ENCLAVE_VERDICT":["bb"*32]},expected_provider_id="provider",expected_key_fingerprint_sha256="aa"*32,expected_nonce="runtime-nonce-0000001",now=dt.datetime(2026,9,18,19,tzinfo=dt.timezone.utc))
        self.assertTrue(rep["verified"])


class V3MigrationTests(unittest.TestCase):
    def test_durable_migration_reservation_stale_writer_and_binding(self):
        records=[UtxoRecord(txid="77"*32,vout=0,amount_sat=100_000,script_type="P2WPKH")]
        batches=build_migration_batches(records,network="SIGNET",manifest_sha256="44"*32,max_inputs_per_batch=10,max_value_sat_per_batch=1_000_000,max_fee_sat_per_batch=10_000)
        with tempfile.TemporaryDirectory() as td:
            store=MigrationStateStore(Path(td)/"state.json")
            state=store.initialize(batches)
            binding=store.reserve(batches[0]["batch_id"],expected_generation=state["generation"],reservation_nonce="migration-nonce-00001",expires_at="2099-01-01T00:00:00Z")
            with self.assertRaises(MigrationEngineError):
                store.reserve(batches[0]["batch_id"],expected_generation=state["generation"],reservation_nonce="migration-nonce-00002",expires_at="2099-01-01T00:00:00Z")
            self.assertEqual(binding.outpoints,("77"*32+":0",))


class V3ControlPlaneTests(unittest.TestCase):
    def policy(self, *, hybrid=False):
        agility=CryptoAgilityPolicy(
            minimum_security_category=1,
            minimum_pq_attestations=2 if hybrid else 0,
            required_pq_families=(AlgorithmFamily.LATTICE,AlgorithmFamily.HASH_BASED) if hybrid else (),
            max_detached_signature_bytes=20_000,
        )
        prime=PrimePolicyProfile("strict-v3",require_source_integrity=True,require_runtime_attestation_for_pq=False)
        return GovernedSigningPolicy(prime=prime,crypto_agility=agility,resource_budget=ResourceBudgetPolicy(),pq_algorithms=("ML-DSA-65","SLH-DSA-SHA2-128s") if hybrid else (),require_quantum_policy_anchor=False)

    def test_integrated_ecdsa_path_reaches_prime_echo_overwatch_and_sara(self):
        root=Path(__file__).resolve().parents[1]/"worldshepherd_qcrypto_kms"
        manifest=build_source_manifest(root)
        gp=self.policy(hybrid=False)
        prep=prepare_governed_signing(make_psbt(),network="SIGNET",policy_state=CryptoPolicyState.ECDSA_ALLOWED,policy_epoch="v3",max_fee_sat=10_000,authorization_nonce="auth-nonce-000000001",expires_at="2099-01-01T00:00:00Z",governed_policy=gp,package_root=root,source_manifest=manifest)
        self.assertTrue(prep.prepared.resource_budget_report.satisfied)
        aps,trusted=approvals(prep.prepared.intent.intent_sha256)
        with tempfile.TemporaryDirectory() as td:
            sara=SaraWorkflowJournal(Path(td)/"sara.jsonl",workflow_id="wf-v3")
            out=authorize_governed_signing(prep,governed_policy=gp,approvals=aps,trusted_approvers=trusted,authorization_ledger_path=str(Path(td)/"auth.jsonl"),sara_workflow_journal=sara)
            self.assertTrue(out["release_authorized_for_local_signing"])
            self.assertEqual(out["sara_workflow"]["state"],"EVIDENCE_COMMITTED")
            self.assertIn("worldshepherd_qcrypto_prime_allowed 1",out["overwatch_openmetrics"])
            self.assertEqual(len(out["echo_evidence_sha256"]),64)

    def test_integrated_two_family_pq_quorum_requires_standard_signature_sizes(self):
        root=Path(__file__).resolve().parents[1]/"worldshepherd_qcrypto_kms"
        manifest=build_source_manifest(root)
        gp=self.policy(hybrid=True)
        prep=prepare_governed_signing(make_psbt(),network="SIGNET",policy_state=CryptoPolicyState.HYBRID_REQUIRED,policy_epoch="v3",max_fee_sat=10_000,authorization_nonce="auth-nonce-000000002",expires_at="2099-01-01T00:00:00Z",governed_policy=gp,package_root=root,source_manifest=manifest,pq_recovery_output_indexes=(0,))
        aps,trusted=approvals(prep.prepared.intent.intent_sha256)
        def provider(pid,alg,fp,size,byte):
            def sign(message,context):
                return bytes([byte])*size, f"{pid}-operation-0001"
            def verify(message,context,signature):
                return signature==bytes([byte])*size
            return CallablePqProviderAdapter(provider_id=pid,algorithm_id=alg,key_fingerprint_sha256=fp,signer=sign,verifier=verify)
        providers=(provider("mldsa","ML-DSA-65","aa"*32,3309,1),provider("slhdsa","SLH-DSA-SHA2-128s","bb"*32,7856,2))
        with tempfile.TemporaryDirectory() as td:
            out=authorize_governed_signing(prep,governed_policy=gp,approvals=aps,trusted_approvers=trusted,pq_providers=providers,authorization_ledger_path=str(Path(td)/"auth.jsonl"))
            self.assertTrue(out["release_authorized_for_local_signing"])
            self.assertEqual(out["pq_quorum"]["verified_count"],2)
            self.assertEqual(set(out["pq_quorum"]["algorithm_agility"]["pq_families"]),{"HASH_BASED","LATTICE"})

    def test_provider_threshold_failover_uses_distinct_provider_without_retrying_failed_one(self):
        root=Path(__file__).resolve().parents[1]/"worldshepherd_qcrypto_kms"
        manifest=build_source_manifest(root)
        agility=CryptoAgilityPolicy(minimum_security_category=1,minimum_pq_attestations=1,required_pq_families=(AlgorithmFamily.LATTICE,),max_detached_signature_bytes=10_000)
        prime=PrimePolicyProfile("threshold-v3",require_source_integrity=True,require_runtime_attestation_for_pq=False)
        gp=GovernedSigningPolicy(prime=prime,crypto_agility=agility,resource_budget=ResourceBudgetPolicy(),pq_algorithms=("ML-DSA-65",),require_quantum_policy_anchor=False)
        prep=prepare_governed_signing(make_psbt(),network="SIGNET",policy_state=CryptoPolicyState.HYBRID_REQUIRED,policy_epoch="v3",max_fee_sat=10_000,authorization_nonce="auth-nonce-000000004",expires_at="2099-01-01T00:00:00Z",governed_policy=gp,package_root=root,source_manifest=manifest,pq_recovery_output_indexes=(0,))
        aps,trusted=approvals(prep.prepared.intent.intent_sha256)
        calls={"failed":0,"good":0}
        def fail_sign(m,c):
            calls["failed"]+=1
            raise RuntimeError("provider unavailable")
        failed=CallablePqProviderAdapter(provider_id="mldsa-a",algorithm_id="ML-DSA-65",key_fingerprint_sha256="cc"*32,signer=fail_sign,verifier=lambda m,c,s:False)
        def good_sign(m,c):
            calls["good"]+=1
            return b"g"*3309,"good-op-1"
        good=CallablePqProviderAdapter(provider_id="mldsa-b",algorithm_id="ML-DSA-65",key_fingerprint_sha256="dd"*32,signer=good_sign,verifier=lambda m,c,s:s==b"g"*3309)
        out=authorize_governed_signing(prep,governed_policy=gp,approvals=aps,trusted_approvers=trusted,pq_providers=(failed,good))
        self.assertTrue(out["release_authorized_for_local_signing"])
        self.assertTrue(out["pq_quorum"]["threshold_failover_used"])
        self.assertEqual(calls,{"failed":1,"good":1})

    def test_malformed_pq_signature_size_is_rejected_before_prime(self):
        root=Path(__file__).resolve().parents[1]/"worldshepherd_qcrypto_kms"
        manifest=build_source_manifest(root)
        gp=self.policy(hybrid=True)
        prep=prepare_governed_signing(make_psbt(),network="SIGNET",policy_state=CryptoPolicyState.HYBRID_REQUIRED,policy_epoch="v3",max_fee_sat=10_000,authorization_nonce="auth-nonce-000000003",expires_at="2099-01-01T00:00:00Z",governed_policy=gp,package_root=root,source_manifest=manifest,pq_recovery_output_indexes=(0,))
        aps,trusted=approvals(prep.prepared.intent.intent_sha256)
        bad=CallablePqProviderAdapter(provider_id="mldsa",algorithm_id="ML-DSA-65",key_fingerprint_sha256="aa"*32,signer=lambda m,c:(b"x","op"),verifier=lambda m,c,s:True)
        good=CallablePqProviderAdapter(provider_id="slhdsa",algorithm_id="SLH-DSA-SHA2-128s",key_fingerprint_sha256="bb"*32,signer=lambda m,c:(b"y"*7856,"op2"),verifier=lambda m,c,s:s==b"y"*7856)
        with self.assertRaises(Exception):
            authorize_governed_signing(prep,governed_policy=gp,approvals=aps,trusted_approvers=trusted,pq_providers=(bad,good))


if __name__=="__main__":
    unittest.main()
