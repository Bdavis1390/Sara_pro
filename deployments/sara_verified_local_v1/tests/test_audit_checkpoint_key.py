from __future__ import annotations

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from worldshepherd_sara.audit_checkpoint_guarded import (
    GuardedSaraAuditCheckpointManager,
)
from worldshepherd_sara.audit_checkpoint_key import (
    AUDIT_CHECKPOINT_KEY_ID_ENV,
    AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV,
    SaraAuditCheckpointKeyConfigError,
    load_audit_checkpoint_key_id,
    load_audit_checkpoint_private_key,
)
from worldshepherd_sara.storage import DurableStore


def _write_key(path, key: Ed25519PrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    path.chmod(0o600)


def test_guarded_manager_uses_dedicated_sara_key_environment(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    path = (tmp_path / "sara-audit-checkpoint.pem").resolve()
    _write_key(path, key)
    monkeypatch.setenv(AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV, str(path))
    monkeypatch.setenv(AUDIT_CHECKPOINT_KEY_ID_ENV, "SARA-AUDIT-KEY-TEST-V1")
    monkeypatch.setenv("ECHO_CHECKPOINT_PRIVATE_KEY_FILE", "/definitely/not/used")
    monkeypatch.setenv("ECHO_CHECKPOINT_KEY_ID", "ECHO-UNRELATED-KEY")

    store = DurableStore(tmp_path / "sara")
    manager = GuardedSaraAuditCheckpointManager.from_environment(store)
    assert manager.key_id == "SARA-AUDIT-KEY-TEST-V1"
    assert manager.private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ) == key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def test_private_key_requires_absolute_path(tmp_path, monkeypatch):
    monkeypatch.setenv(AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV, "relative.pem")
    with pytest.raises(SaraAuditCheckpointKeyConfigError, match="absolute path"):
        load_audit_checkpoint_private_key()


def test_private_key_rejects_group_or_other_permissions(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    path = (tmp_path / "permissive.pem").resolve()
    _write_key(path, key)
    path.chmod(0o640)
    monkeypatch.setenv(AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV, str(path))
    with pytest.raises(SaraAuditCheckpointKeyConfigError, match="group/other"):
        load_audit_checkpoint_private_key()


def test_private_key_rejects_symlink(tmp_path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    target = (tmp_path / "target.pem").resolve()
    _write_key(target, key)
    link = tmp_path / "link.pem"
    link.symlink_to(target)
    monkeypatch.setenv(AUDIT_CHECKPOINT_PRIVATE_KEY_FILE_ENV, str(link.absolute()))
    with pytest.raises(SaraAuditCheckpointKeyConfigError, match="symbolic link"):
        load_audit_checkpoint_private_key()


def test_key_id_is_bounded_safe_identifier(monkeypatch):
    monkeypatch.setenv(AUDIT_CHECKPOINT_KEY_ID_ENV, "SARA-AUDIT-KEY:PROD.1")
    assert load_audit_checkpoint_key_id() == "SARA-AUDIT-KEY:PROD.1"
    monkeypatch.setenv(AUDIT_CHECKPOINT_KEY_ID_ENV, "bad key id with spaces")
    with pytest.raises(SaraAuditCheckpointKeyConfigError, match="safe identifier"):
        load_audit_checkpoint_key_id()
