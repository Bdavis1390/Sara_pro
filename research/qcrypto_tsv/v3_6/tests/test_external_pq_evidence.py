import copy
import hashlib
import json
import unittest
from pathlib import Path

from tests.test_v3_control_plane import make_psbt
from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.external_parser_quorum import validate_external_parser_quorum_report
from worldshepherd_qcrypto_kms.external_pq_evidence import (
    ExternalPqEvidenceError,
    build_external_pq_candidate_challenge,
    validate_external_pq_evidence_report,
)
from worldshepherd_qcrypto_kms.signing_gate import SigningGateError, prepare_psbt_signing
from worldshepherd_qcrypto_kms.control_plane import ControlPlaneError, GovernedSigningPolicy, prepare_governed_signing
from worldshepherd_qcrypto_kms.crypto_agility import AlgorithmFamily, CryptoAgilityPolicy
from worldshepherd_qcrypto_kms.governance_plane import PrimePolicyProfile
from worldshepherd_qcrypto_kms.resource_budget import ResourceBudgetPolicy
from worldshepherd_qcrypto_kms.source_integrity import build_source_manifest

ROOT = Path(__file__).resolve().parents[1]
PQ_REPORT = json.loads((ROOT / "evidence" / "EXTERNAL_PQ_CANDIDATE_QUORUM_V1.json").read_text())
PARSER_REPORT = json.loads((ROOT / "evidence" / "EXTERNAL_PARSER_QUORUM_RECEIPT_V1.json").read_text())
ALGS = ("ML-DSA-65", "SLH-DSA-SHA2-128f")
TXID = "259f20588df355fb3732c1fd4f41d5d8666d1bc512dc83c554515cc1b3d1205d"


def parser_binding(raw: bytes):
    return validate_external_parser_quorum_report(
        PARSER_REPORT,
        expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
        expected_txid=TXID,
        expected_fee_sat=1000,
    )


class ExternalPqEvidenceTests(unittest.TestCase):
    def test_candidate_challenge_matches_external_execution(self):
        raw = make_psbt()
        pb = parser_binding(raw)
        text = build_external_pq_candidate_challenge(
            psbt_sha256=hashlib.sha256(raw).hexdigest(),
            txid=TXID,
            fee_sat=1000,
            external_parser_receipt_sha256=pb.receipt_sha256,
            policy_epoch="v3.2",
            algorithms=ALGS,
        )
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), PQ_REPORT["candidate_challenge_sha256"])

    def test_actual_hosted_pq_receipt_binds_exact_candidate(self):
        raw = make_psbt()
        pb = parser_binding(raw)
        binding = validate_external_pq_evidence_report(
            PQ_REPORT,
            expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
            expected_txid=TXID,
            expected_fee_sat=1000,
            expected_parser_receipt_sha256=pb.receipt_sha256,
            policy_epoch="v3.2",
            required_algorithms=ALGS,
            minimum_execution_targets=1,
            require_family_diversity=True,
        )
        self.assertEqual(binding.algorithms, ALGS)
        self.assertEqual(set(binding.pq_families), {"LATTICE", "HASH_BASED"})
        self.assertEqual(binding.execution_targets, ("Supabase Edge Function",))
        self.assertEqual(len(binding.receipt_sha256), 64)

    def test_signing_gate_can_require_candidate_bound_external_pq_evidence(self):
        raw = make_psbt()
        prepared = prepare_psbt_signing(
            raw,
            network="SIGNET",
            policy_state=CryptoPolicyState.ECDSA_ALLOWED,
            policy_epoch="v3.2",
            max_fee_sat=10_000,
            authorization_nonce="external-pq-candidate-0001",
            expires_at="2099-01-01T00:00:00Z",
            detached_pq_algorithms=ALGS,
            external_parser_quorum_report=PARSER_REPORT,
            require_external_parser_quorum=True,
            external_pq_evidence_report=PQ_REPORT,
            require_external_pq_evidence=True,
            require_external_pq_family_diversity=True,
        )
        row = prepared.external_pq_evidence_binding
        self.assertIsNotNone(row)
        self.assertEqual(row["candidate_challenge_sha256"], PQ_REPORT["candidate_challenge_sha256"])
        self.assertTrue(prepared.to_dict()["ready_for_local_authorization"])

    def test_missing_required_external_pq_evidence_fails_closed(self):
        raw = make_psbt()
        with self.assertRaises(SigningGateError):
            prepare_psbt_signing(
                raw,
                network="SIGNET",
                policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                policy_epoch="v3.2",
                max_fee_sat=10_000,
                authorization_nonce="external-pq-candidate-0002",
                expires_at="2099-01-01T00:00:00Z",
                detached_pq_algorithms=ALGS,
                external_parser_quorum_report=PARSER_REPORT,
                require_external_parser_quorum=True,
                require_external_pq_evidence=True,
            )

    def test_wrong_challenge_fails_closed(self):
        raw = make_psbt()
        pb = parser_binding(raw)
        bad = copy.deepcopy(PQ_REPORT)
        bad["candidate_challenge_sha256"] = "00" * 32
        with self.assertRaises(ExternalPqEvidenceError):
            validate_external_pq_evidence_report(
                bad,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=TXID,
                expected_fee_sat=1000,
                expected_parser_receipt_sha256=pb.receipt_sha256,
                policy_epoch="v3.2",
                required_algorithms=ALGS,
            )

    def test_signature_size_mismatch_fails_closed(self):
        raw = make_psbt()
        pb = parser_binding(raw)
        bad = copy.deepcopy(PQ_REPORT)
        bad["executions"][0]["signature_bytes"] = 3308
        with self.assertRaises(ExternalPqEvidenceError):
            validate_external_pq_evidence_report(
                bad,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=TXID,
                expected_fee_sat=1000,
                expected_parser_receipt_sha256=pb.receipt_sha256,
                policy_epoch="v3.2",
                required_algorithms=ALGS,
            )

    def test_failed_tamper_control_fails_closed(self):
        raw = make_psbt()
        pb = parser_binding(raw)
        bad = copy.deepcopy(PQ_REPORT)
        bad["executions"][1]["tampered_signature_rejected"] = False
        with self.assertRaises(ExternalPqEvidenceError):
            validate_external_pq_evidence_report(
                bad,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=TXID,
                expected_fee_sat=1000,
                expected_parser_receipt_sha256=pb.receipt_sha256,
                policy_epoch="v3.2",
                required_algorithms=ALGS,
            )

    def test_integrated_governed_policy_can_mandate_external_parser_and_pq_evidence(self):
        raw = make_psbt()
        package_root = ROOT / "worldshepherd_qcrypto_kms"
        manifest = build_source_manifest(package_root)
        policy = GovernedSigningPolicy(
            prime=PrimePolicyProfile("external-evidence-v3.2", require_source_integrity=True, require_runtime_attestation_for_pq=False),
            crypto_agility=CryptoAgilityPolicy(
                minimum_pq_attestations=2,
                required_pq_families=(AlgorithmFamily.LATTICE, AlgorithmFamily.HASH_BASED),
                max_detached_signature_bytes=25_000,
            ),
            resource_budget=ResourceBudgetPolicy(max_detached_pq_signature_bytes=25_000),
            pq_algorithms=ALGS,
            require_quantum_policy_anchor=False,
            require_external_parser_quorum=True,
            require_external_pq_evidence=True,
            require_external_pq_family_diversity=True,
        )
        prep = prepare_governed_signing(
            raw, network="SIGNET", policy_state=CryptoPolicyState.HYBRID_REQUIRED, policy_epoch="v3.2",
            max_fee_sat=10_000, authorization_nonce="external-governed-pq-0001", expires_at="2099-01-01T00:00:00Z",
            governed_policy=policy, package_root=package_root, source_manifest=manifest, pq_recovery_output_indexes=(0,),
            external_parser_quorum_report=PARSER_REPORT, external_pq_evidence_report=PQ_REPORT,
        )
        self.assertEqual(prep.prepared.external_pq_evidence_binding["candidate_challenge_sha256"], PQ_REPORT["candidate_challenge_sha256"])
        self.assertEqual(prep.prepared.external_parser_quorum_binding["txid"], TXID)

    def test_integrated_governed_policy_missing_external_pq_receipt_fails_closed(self):
        raw = make_psbt()
        package_root = ROOT / "worldshepherd_qcrypto_kms"
        manifest = build_source_manifest(package_root)
        policy = GovernedSigningPolicy(
            prime=PrimePolicyProfile("external-evidence-v3.2", require_source_integrity=True, require_runtime_attestation_for_pq=False),
            crypto_agility=CryptoAgilityPolicy(
                minimum_pq_attestations=2,
                required_pq_families=(AlgorithmFamily.LATTICE, AlgorithmFamily.HASH_BASED),
                max_detached_signature_bytes=25_000,
            ),
            resource_budget=ResourceBudgetPolicy(max_detached_pq_signature_bytes=25_000),
            pq_algorithms=ALGS, require_quantum_policy_anchor=False,
            require_external_parser_quorum=True, require_external_pq_evidence=True, require_external_pq_family_diversity=True,
        )
        with self.assertRaises(ControlPlaneError):
            prepare_governed_signing(
                raw, network="SIGNET", policy_state=CryptoPolicyState.HYBRID_REQUIRED, policy_epoch="v3.2",
                max_fee_sat=10_000, authorization_nonce="external-governed-pq-0002", expires_at="2099-01-01T00:00:00Z",
                governed_policy=policy, package_root=package_root, source_manifest=manifest, pq_recovery_output_indexes=(0,),
                external_parser_quorum_report=PARSER_REPORT,
            )

    def test_family_diversity_fails_closed_when_required(self):
        raw = make_psbt()
        pb = parser_binding(raw)
        single = copy.deepcopy(PQ_REPORT)
        single["executions"] = [single["executions"][0]]
        single["required_algorithms"] = ["ML-DSA-65"]
        # The challenge must be rebuilt for the one-algorithm set; this ensures the
        # failure comes from family diversity rather than stale candidate binding.
        text = build_external_pq_candidate_challenge(
            psbt_sha256=hashlib.sha256(raw).hexdigest(), txid=TXID, fee_sat=1000,
            external_parser_receipt_sha256=pb.receipt_sha256, policy_epoch="v3.2",
            algorithms=("ML-DSA-65",),
        )
        challenge_sha = hashlib.sha256(text.encode()).hexdigest()
        single["candidate_challenge_sha256"] = challenge_sha
        single["executions"][0]["candidate_challenge_sha256"] = challenge_sha
        with self.assertRaises(ExternalPqEvidenceError):
            validate_external_pq_evidence_report(
                single,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(), expected_txid=TXID,
                expected_fee_sat=1000, expected_parser_receipt_sha256=pb.receipt_sha256,
                policy_epoch="v3.2", required_algorithms=("ML-DSA-65",),
                require_family_diversity=True,
            )


if __name__ == "__main__":
    unittest.main()
