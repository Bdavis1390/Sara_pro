import copy
import hashlib
import unittest

from tests.test_v3_control_plane import make_psbt
from worldshepherd_qcrypto_kms.bitcoin_quantum_policy import CryptoPolicyState
from worldshepherd_qcrypto_kms.external_parser_quorum import (
    ExternalParserQuorumError,
    validate_external_parser_quorum_report,
)
from worldshepherd_qcrypto_kms.signing_gate import SigningGateError, prepare_psbt_signing


TXID = "259f20588df355fb3732c1fd4f41d5d8666d1bc512dc83c554515cc1b3d1205d"
FEE = 1000


def quorum_report(raw: bytes) -> dict:
    row = {
        "txid": TXID,
        "inputs": 1,
        "outputs": 1,
        "input_value_sat": "100000",
        "output_value_sat": "99000",
        "fee_sat": "1000",
        "first_output_script": "00141111111111111111111111111111111111111111",
    }
    return {
        "schema": "WS-QCRYPTO-EXTERNAL-BITCOIN-PARSER-QUORUM-V1",
        "execution_location": "Supabase Edge Function",
        "libraries": ["bitcoinjs-lib@7.0.0", "@scure/btc-signer@2.4.1"],
        "psbt_sha256": hashlib.sha256(raw).hexdigest(),
        "bitcoinjs": dict(row),
        "scure": dict(row),
        "agreement": True,
        "release_allowed": True,
        "verdict_sha256": "c0f3f6f4865a00c47e5b3b0f2e0ccdab7dced2e2cf340e83bb9fd0ea7749e0d6",
        "generated_at": "2026-09-18T21:23:19.728Z",
    }


class ExternalParserQuorumTests(unittest.TestCase):
    def test_actual_external_receipt_shape_binds_exact_candidate(self):
        raw = make_psbt()
        binding = validate_external_parser_quorum_report(
            quorum_report(raw),
            expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
            expected_txid=TXID,
            expected_fee_sat=FEE,
        )
        self.assertEqual(binding.txid, TXID)
        self.assertEqual(binding.fee_sat, FEE)
        self.assertEqual(len(binding.libraries), 2)
        self.assertEqual(len(binding.receipt_sha256), 64)

    def test_signing_gate_can_require_external_parser_quorum(self):
        raw = make_psbt()
        prepared = prepare_psbt_signing(
            raw,
            network="SIGNET",
            policy_state=CryptoPolicyState.ECDSA_ALLOWED,
            policy_epoch="v3.1",
            max_fee_sat=10_000,
            authorization_nonce="external-quorum-0000001",
            expires_at="2099-01-01T00:00:00Z",
            external_parser_quorum_report=quorum_report(raw),
            require_external_parser_quorum=True,
        )
        self.assertEqual(prepared.external_parser_quorum_binding["txid"], TXID)
        self.assertEqual(prepared.external_parser_quorum_binding["fee_sat"], FEE)
        self.assertTrue(prepared.to_dict()["ready_for_local_authorization"])

    def test_missing_required_external_quorum_fails_closed(self):
        raw = make_psbt()
        with self.assertRaises(SigningGateError):
            prepare_psbt_signing(
                raw,
                network="SIGNET",
                policy_state=CryptoPolicyState.ECDSA_ALLOWED,
                policy_epoch="v3.1",
                max_fee_sat=10_000,
                authorization_nonce="external-quorum-0000002",
                expires_at="2099-01-01T00:00:00Z",
                require_external_parser_quorum=True,
            )

    def test_parser_txid_disagreement_fails_closed(self):
        raw = make_psbt()
        bad = copy.deepcopy(quorum_report(raw))
        bad["scure"]["txid"] = "00" * 32
        with self.assertRaises(ExternalParserQuorumError):
            validate_external_parser_quorum_report(
                bad,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=TXID,
                expected_fee_sat=FEE,
            )

    def test_parser_fee_disagreement_fails_closed(self):
        raw = make_psbt()
        bad = copy.deepcopy(quorum_report(raw))
        bad["bitcoinjs"]["fee_sat"] = "999"
        with self.assertRaises(ExternalParserQuorumError):
            validate_external_parser_quorum_report(
                bad,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=TXID,
                expected_fee_sat=FEE,
            )

    def test_single_library_does_not_satisfy_quorum(self):
        raw = make_psbt()
        bad = copy.deepcopy(quorum_report(raw))
        bad["libraries"] = ["bitcoinjs-lib@7.0.0"]
        with self.assertRaises(ExternalParserQuorumError):
            validate_external_parser_quorum_report(
                bad,
                expected_psbt_sha256=hashlib.sha256(raw).hexdigest(),
                expected_txid=TXID,
                expected_fee_sat=FEE,
            )


if __name__ == "__main__":
    unittest.main()
