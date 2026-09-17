from __future__ import annotations

import multiprocessing
import os
import stat
import time
from datetime import timedelta

import pytest

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
from qcrypto_external_signer.unix_provider import (
    ProviderRpcError,
    UnixOpaqueSignerProviderClient,
    serve_reference_provider,
)
from tests.test_custody import fixture


class CountingUnixProviderClient(UnixOpaqueSignerProviderClient):
    def __init__(self, socket_path):
        self.begin_sign_calls = 0
        self.reconcile_calls = 0
        super().__init__(socket_path)

    def begin_sign(self, operation_id: str, message: bytes, context: bytes):
        self.begin_sign_calls += 1
        return super().begin_sign(operation_id, message, context)

    def reconcile(self, operation_id: str):
        self.reconcile_calls += 1
        return super().reconcile(operation_id)


def _start_signer(tmp_path, *, ack_loss_once: bool):
    socket_dir = tmp_path / "signer-private"
    socket_dir.mkdir(mode=0o700)
    socket_path = socket_dir / "opaque-signer.sock"
    ctx = multiprocessing.get_context("fork")
    proc = ctx.Process(
        target=serve_reference_provider,
        args=(socket_path,),
        kwargs={"ack_loss_once": ack_loss_once},
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
    raise AssertionError("opaque signer subprocess did not create its Unix socket")


def _custody(tmp_path, signer, human_public):
    return OpaqueProviderCustodyService(
        ledger=CustodyLedger(tmp_path / "custody-ledger.json"),
        signer=signer,
        policy=CustodyPolicy.testnet_reference(),
        trusted_human_keys={"HUMAN-MLDSA65-TEST": human_public},
    )


def test_separate_signer_process_reconciles_ack_loss_without_second_sign_call(tmp_path):
    proc, socket_path = _start_signer(tmp_path, ack_loss_once=True)
    try:
        client = CountingUnixProviderClient(socket_path)
        assert client.descriptor.signer_process_id == proc.pid
        assert client.descriptor.signer_process_id != os.getpid()
        assert not hasattr(client, "private_key_bytes")
        assert not hasattr(client, "export_private_key")

        socket_mode = stat.S_IMODE(socket_path.stat().st_mode)
        directory_mode = stat.S_IMODE(socket_path.parent.stat().st_mode)
        assert socket_mode == 0o600
        assert directory_mode & 0o077 == 0

        signer = OpaqueProviderReleaseSigner(client)
        request, _ignored, human_public, now = fixture(signer=signer)
        custody = _custody(tmp_path, signer, human_public)

        with pytest.raises(CustodyIndeterminate, match="reconcile"):
            custody.execute_release(request, now=now + timedelta(seconds=1))
        assert client.begin_sign_calls == 1
        assert client.reconcile_calls == 0

        receipt = custody.reconcile_release(request)
        assert client.begin_sign_calls == 1
        assert client.reconcile_calls == 1
        assert receipt["provider_reconciled"] is True
        assert verify_opaque_provider_receipt(
            receipt,
            public_key_bytes=client.public_key_bytes,
        )

        # Recreate both custody client-side objects while leaving only the signer
        # subprocess/provider state alive. Exact post-expiry retrieval is local ledger
        # recovery and does not call begin_sign or reconcile again.
        client_after_restart = CountingUnixProviderClient(socket_path)
        signer_after_restart = OpaqueProviderReleaseSigner(client_after_restart)
        recovered = _custody(tmp_path, signer_after_restart, human_public).execute_release(
            request,
            now=now + timedelta(minutes=20),
        )
        assert recovered == receipt
        assert client_after_restart.begin_sign_calls == 0
        assert client_after_restart.reconcile_calls == 0
    finally:
        proc.terminate()
        proc.join(timeout=2)


def test_signer_rpc_has_no_private_key_export_command(tmp_path):
    proc, socket_path = _start_signer(tmp_path, ack_loss_once=False)
    try:
        client = UnixOpaqueSignerProviderClient(socket_path)
        with pytest.raises(ProviderRpcError, match="INVALID_REQUEST"):
            client._rpc({"command": "export_private_key"})
    finally:
        proc.terminate()
        proc.join(timeout=2)
