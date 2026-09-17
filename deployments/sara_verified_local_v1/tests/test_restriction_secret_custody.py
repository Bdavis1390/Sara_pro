from __future__ import annotations

import os

import pytest

from worldshepherd_sara.restriction_provenance import (
    ALLOW_LEGACY_FINGERPRINT_KEY_ENV,
    FINGERPRINT_KEY_FILE_ENV,
    LEGACY_FINGERPRINT_KEY_ENV,
    RestrictionProvenanceError,
    fingerprint_key_from_environment,
)


BASELINE_RESIDUAL_RISK_UNITS = 6
MAX_RESIDUAL_RATIO = 0.10
KEY = b"g7-file-backed-restriction-key-32-bytes-minimum"


def _clear(monkeypatch):
    for name in (
        FINGERPRINT_KEY_FILE_ENV,
        LEGACY_FINGERPRINT_KEY_ENV,
        ALLOW_LEGACY_FINGERPRINT_KEY_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


def _secure_key_file(tmp_path, data=KEY):
    path = tmp_path / "restriction-fingerprint.key"
    path.write_bytes(data)
    path.chmod(0o600)
    return path


def _accepts(monkeypatch, *, file_value=None, legacy_value=None, allow_legacy=None):
    _clear(monkeypatch)
    if file_value is not None:
        monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(file_value))
    if legacy_value is not None:
        monkeypatch.setenv(LEGACY_FINGERPRINT_KEY_ENV, legacy_value)
    if allow_legacy is not None:
        monkeypatch.setenv(ALLOW_LEGACY_FINGERPRINT_KEY_ENV, allow_legacy)
    try:
        fingerprint_key_from_environment()
        return True
    except RestrictionProvenanceError:
        return False


def test_secure_absolute_owner_only_key_file_loads(monkeypatch, tmp_path):
    path = _secure_key_file(tmp_path)
    _clear(monkeypatch)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(path.resolve()))
    assert fingerprint_key_from_environment() == KEY


def test_legacy_environment_secret_requires_explicit_compatibility_opt_in(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv(LEGACY_FINGERPRINT_KEY_ENV, "x" * 40)
    with pytest.raises(RestrictionProvenanceError, match="environment fingerprint-key custody is disabled"):
        fingerprint_key_from_environment()

    monkeypatch.setenv(ALLOW_LEGACY_FINGERPRINT_KEY_ENV, "true")
    assert fingerprint_key_from_environment() == b"x" * 40


def test_dual_key_sources_fail_closed(monkeypatch, tmp_path):
    path = _secure_key_file(tmp_path)
    _clear(monkeypatch)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(path.resolve()))
    monkeypatch.setenv(LEGACY_FINGERPRINT_KEY_ENV, "x" * 40)
    monkeypatch.setenv(ALLOW_LEGACY_FINGERPRINT_KEY_ENV, "true")
    with pytest.raises(RestrictionProvenanceError, match="exactly one"):
        fingerprint_key_from_environment()


def test_relative_key_path_fails_closed(monkeypatch, tmp_path):
    path = _secure_key_file(tmp_path)
    _clear(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, path.name)
    with pytest.raises(RestrictionProvenanceError, match="absolute path"):
        fingerprint_key_from_environment()


def test_symlink_key_path_fails_closed(monkeypatch, tmp_path):
    target = _secure_key_file(tmp_path)
    link = tmp_path / "restriction-fingerprint-link"
    link.symlink_to(target)
    _clear(monkeypatch)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(link.resolve(strict=False)))
    # resolve() follows the link, so explicitly pass the symlink's absolute lexical path.
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, os.path.abspath(link))
    with pytest.raises(RestrictionProvenanceError, match="symbolic link"):
        fingerprint_key_from_environment()


def test_group_or_other_readable_key_file_fails_closed(monkeypatch, tmp_path):
    path = _secure_key_file(tmp_path)
    path.chmod(0o640)
    _clear(monkeypatch)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(path.resolve()))
    with pytest.raises(RestrictionProvenanceError, match="group/other permissions"):
        fingerprint_key_from_environment()


def test_undersized_key_file_fails_closed(monkeypatch, tmp_path):
    path = _secure_key_file(tmp_path, b"too-short")
    _clear(monkeypatch)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(path.resolve()))
    with pytest.raises(RestrictionProvenanceError, match="size is invalid"):
        fingerprint_key_from_environment()


def test_g7_software_custody_reduces_declared_exposure_paths_by_at_least_ten_x(
    monkeypatch, tmp_path
):
    secure = _secure_key_file(tmp_path)
    weak = tmp_path / "weak.key"
    weak.write_bytes(KEY)
    weak.chmod(0o644)
    short = tmp_path / "short.key"
    short.write_bytes(b"short")
    short.chmod(0o600)
    link = tmp_path / "link.key"
    link.symlink_to(secure)

    residual = sum(
        int(value)
        for value in (
            _accepts(monkeypatch, legacy_value="x" * 40),
            _accepts(
                monkeypatch,
                file_value=secure.resolve(),
                legacy_value="x" * 40,
                allow_legacy="true",
            ),
            _accepts(monkeypatch, file_value="relative.key"),
            _accepts(monkeypatch, file_value=os.path.abspath(link)),
            _accepts(monkeypatch, file_value=weak.resolve()),
            _accepts(monkeypatch, file_value=short.resolve()),
        )
    )

    assert BASELINE_RESIDUAL_RISK_UNITS == 6
    assert residual / BASELINE_RESIDUAL_RISK_UNITS <= MAX_RESIDUAL_RATIO
    assert residual == 0


def test_g7_claim_boundary_is_not_hardware_backed(monkeypatch, tmp_path):
    path = _secure_key_file(tmp_path)
    _clear(monkeypatch)
    monkeypatch.setenv(FINGERPRINT_KEY_FILE_ENV, str(path.resolve()))
    assert fingerprint_key_from_environment() == KEY
    # This proves only the local file-custody invariants tested above.
    # It does not prove HSM/TPM custody, external KMS custody, or independent validation.
