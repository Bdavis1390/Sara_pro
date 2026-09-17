#!/usr/bin/env python3
"""Retained evidence for the separate Unix-domain opaque signer process boundary."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import stat
import tempfile
import time
from datetime import timedelta
from pathlib import Path

from qcrypto_external_signer.custody import (
    CustodyIndeterminate,
    CustodyLedger,
    CustodyPolicy,
)
from qcrypto_external_signer.opaque_provider import OpaqueProviderReleaseSigner
from qcrypto_external_signer.provider_custody import (
    OpaqueProviderCustodyService,
    verify_opaque_provider_receipt,
)
from qcrypto_external_signer.synthetic import build_synthetic_request
from qcrypto_external_signer.unix_provider import (
    ProviderRpcError,
    UnixOpaqueSignerProviderClient,
    serve_reference_provider,
)


class CountingUnixProviderClient(UnixOpaqueSignerProviderClient):
    def __init__(self, socket_path: str | Path) -> None:
        self.begin_sign_calls = 0
        self.reconcile_calls = 0
        super().__init__(socket_path)

    def begin_sign(self, operation_id: str, message: bytes, context: bytes):
        self.begin_sign_calls += 1
        return super().begin_sign(operation_id, message, context)

    def reconcile(self, operation_id: str):
        self.reconcile_calls += 1
        return super().reconcile(operation_id)


def canonical_sha(value: dict) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def custody(root: Path, signer: OpaqueProviderReleaseSigner, human_public: bytes) -> OpaqueProviderCustodyService:
    return OpaqueProviderCustodyService(
        ledger=CustodyLedger(root / "custody-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def start_signer(root: Path):
    private_dir = root / "signer-private"
    private_dir.mkdir(mode=0o700)
    socket_path = private_dir / "opaque-signer.sock"
    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(
        target=serve_reference_provider,
        args=(socket_path,),
        kwargs={"ack_loss_once": True},
        daemon=True,
    )
    proc.start()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if socket_path.exists():
            return proc, socket_path
        if not proc.is_alive():
            break
        time.sleep(0.02)
    proc.terminate()
    proc.join(timeout=2)
    raise RuntimeError("separate signer process did not create its Unix socket")


def export_rpc_rejected(client: UnixOpaqueSignerProviderClient) -> bool:
    try:
        client._rpc({"command": "export_private_key"})
    except ProviderRpcError:
        return True
    return False


def tcp_connect_surface_absent(socket_path: Path) -> bool:
    mode = socket_path.stat().st_mode
    return stat.S_ISSOCK(mode) and not hasattr(UnixOpaqueSignerProviderClient, "host")


def build_evidence() -> dict:
    parent_pid = os.getpid()
    with tempfile.TemporaryDirectory(prefix="ws-qcrypto-unix-signer-") as tmp:
        root = Path(tmp)
        proc, socket_path = start_signer(root)
        try:
            client = CountingUnixProviderClient(socket_path)
            signer = OpaqueProviderReleaseSigner(client)
            request, _ignored, human_public, now = build_synthetic_request(signer=signer)
            service = custody(root, signer, human_public)

            child_pid = client.descriptor.signer_process_id
            socket_mode = stat.S_IMODE(socket_path.stat().st_mode)
            directory_mode = stat.S_IMODE(socket_path.parent.stat().st_mode)
            socket_is_unix = stat.S_ISSOCK(socket_path.stat().st_mode)
            no_key_export_attribute = (
                not hasattr(client, "private_key_bytes")
                and not hasattr(client, "export_private_key")
            )
            export_rejected = export_rpc_rejected(client)
            no_tcp_surface = tcp_connect_surface_absent(socket_path)

            ambiguous_fail_stop = False
            try:
                service.execute_release(request, now=now + timedelta(seconds=1))
            except CustodyIndeterminate:
                ambiguous_fail_stop = True

            begin_before_reconcile = client.begin_sign_calls
            reconcile_before = client.reconcile_calls
            receipt = service.reconcile_release(request)
            begin_after_reconcile = client.begin_sign_calls
            reconcile_after = client.reconcile_calls
            receipt_verified = verify_opaque_provider_receipt(
                receipt,
                public_key_bytes=client.public_key_bytes,
            )

            restarted_client = CountingUnixProviderClient(socket_path)
            restarted_signer = OpaqueProviderReleaseSigner(restarted_client)
            post_expiry = custody(root, restarted_signer, human_public).execute_release(
                request,
                now=now + timedelta(minutes=20),
            )
            post_expiry_identical = post_expiry == receipt

            ledger = json.loads((root / "custody-ledger.json").read_text(encoding="utf-8"))
            entry = ledger["requests"][request["request_id"]]

            evidence = {
                "schema": "WS-QCRYPTO-UNIX-SIGNER-BOUNDARY-EVIDENCE-V1",
                "status": "PASS",
                "claim_state": "SEPARATE_SIGNER_PROCESS_SOFTWARE_BEHAVIOR_ONLY",
                "synthetic_ci_only": True,
                "custody_process_id": parent_pid,
                "signer_process_id": child_pid,
                "signer_process_separate": child_pid == proc.pid and child_pid != parent_pid,
                "transport": "UNIX_DOMAIN_SOCKET_ONLY",
                "socket_is_unix_domain": socket_is_unix,
                "socket_mode_octal": oct(socket_mode),
                "socket_owner_read_write_only": socket_mode == 0o600,
                "socket_directory_mode_octal": oct(directory_mode),
                "socket_directory_not_group_world_accessible": directory_mode & 0o077 == 0,
                "private_key_export_attribute_absent": no_key_export_attribute,
                "private_key_export_rpc_rejected": export_rejected,
                "tcp_transport_surface_absent": no_tcp_surface,
                "remote_algorithm": client.algorithm,
                "remote_key_handle": client.key_handle,
                "remote_public_key_fingerprint_sha256": client.fingerprint_sha256,
                "provider_ack_loss_fail_stopped": ambiguous_fail_stop,
                "outbound_begin_sign_calls_before_reconcile": begin_before_reconcile,
                "outbound_begin_sign_calls_after_reconcile": begin_after_reconcile,
                "outbound_reconcile_calls_before_reconcile": reconcile_before,
                "outbound_reconcile_calls_after_reconcile": reconcile_after,
                "reconciliation_did_not_issue_second_sign_call": (
                    begin_before_reconcile == begin_after_reconcile == 1
                    and reconcile_before == 0
                    and reconcile_after == 1
                ),
                "receipt_verified": receipt_verified,
                "receipt_provider_reconciled": receipt.get("provider_reconciled") is True,
                "durable_state": entry.get("state"),
                "durable_provider_operation_id_matches_receipt": (
                    entry.get("provider_operation_id") == receipt.get("provider_operation_id")
                ),
                "custody_side_restart_post_expiry_receipt_identical": post_expiry_identical,
                "restart_begin_sign_calls": restarted_client.begin_sign_calls,
                "restart_reconcile_calls": restarted_client.reconcile_calls,
                "production_hsm_integrated": False,
                "fips_validated_module_established": False,
                "native_chain_transaction_signature": False,
                "transaction_broadcast": False,
                "mainnet_permitted": False,
                "real_value_moved": False,
                "federal_compliance_established": False,
                "independent_validation_established": False,
                "end_to_end_pq_chain_security_established": False,
                "receipt": receipt,
                "claims_boundary": (
                    "Synthetic CI proof of a separate signer process using an owner-controlled Unix-domain "
                    "socket and opaque provider interface. This does not establish a production HSM/KMS, "
                    "FIPS validation, native-chain transaction signing, broadcast, mainnet authorization, "
                    "movement of real value, Federal compliance, independent validation, or end-to-end "
                    "post-quantum cryptocurrency security."
                ),
            }

            must_pass = (
                evidence["signer_process_separate"]
                and evidence["socket_is_unix_domain"]
                and evidence["socket_owner_read_write_only"]
                and evidence["socket_directory_not_group_world_accessible"]
                and evidence["private_key_export_attribute_absent"]
                and evidence["private_key_export_rpc_rejected"]
                and evidence["tcp_transport_surface_absent"]
                and evidence["provider_ack_loss_fail_stopped"]
                and evidence["reconciliation_did_not_issue_second_sign_call"]
                and evidence["receipt_verified"]
                and evidence["receipt_provider_reconciled"]
                and evidence["durable_state"] == "SIGNED"
                and evidence["durable_provider_operation_id_matches_receipt"]
                and evidence["custody_side_restart_post_expiry_receipt_identical"]
                and evidence["restart_begin_sign_calls"] == 0
                and evidence["restart_reconcile_calls"] == 0
            )
            if not must_pass:
                raise RuntimeError("separate signer process boundary evidence failed")
            evidence["evidence_sha256"] = canonical_sha(evidence)
            return evidence
        finally:
            proc.terminate()
            proc.join(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evidence = build_evidence()
    Path(args.output).write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("unix_signer_boundary_evidence: PASS")
    print("signer_process_id:", evidence["signer_process_id"])
    print("evidence_sha256:", evidence["evidence_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
