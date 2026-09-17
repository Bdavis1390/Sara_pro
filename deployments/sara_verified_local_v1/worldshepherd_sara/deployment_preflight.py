from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any


_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SECRET_KEYS = ("SARA_RELAY_TOKEN", "SARA_ADMIN_TOKEN")
_SECRET_FILES = (
    "PRIME_SENTINEL_PRIVATE_KEY_HOST_PATH",
    "PRIME_SENTINEL_SERVICE_TOKEN_HOST_PATH",
    "ECHO_INGEST_TOKEN_HOST_PATH",
    "ECHO_CHECKPOINT_PRIVATE_KEY_HOST_PATH",
)
_PLACEHOLDERS = ("replace-", "unknown", "unverified", "unconfigured")


class DeploymentPreflightError(ValueError):
    pass


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DeploymentPreflightError("environment line is missing '='")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _required(values: dict[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise DeploymentPreflightError(f"{name} is required")
    return value


def _reject_placeholder(name: str, value: str) -> None:
    lowered = value.strip().lower()
    if any(marker in lowered for marker in _PLACEHOLDERS):
        raise DeploymentPreflightError(f"{name} still contains a placeholder value")


def _port(values: dict[str, str], name: str, default: int) -> int:
    raw = values.get(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise DeploymentPreflightError(f"{name} must be an integer") from exc
    if not 1 <= value <= 65535:
        raise DeploymentPreflightError(f"{name} must be 1-65535")
    return value


def _secret_file(
    values: dict[str, str],
    name: str,
    *,
    required_uid: int,
) -> dict[str, Any]:
    raw = _required(values, name)
    path = Path(raw)
    if not path.is_absolute():
        raise DeploymentPreflightError(f"{name} must be an absolute path")
    try:
        info = path.lstat()
    except OSError as exc:
        raise DeploymentPreflightError(f"{name} does not exist") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise DeploymentPreflightError(f"{name} must be a regular non-symlink file")
    if info.st_uid != required_uid:
        raise DeploymentPreflightError(
            f"{name} must be owned by UID {required_uid}; found {info.st_uid}"
        )
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o077:
        raise DeploymentPreflightError(f"{name} must not grant group/other permissions")
    if info.st_size < 1 or info.st_size > 16 * 1024:
        raise DeploymentPreflightError(f"{name} size is outside the allowed bound")
    return {
        "path": str(path),
        "owner_uid": info.st_uid,
        "mode": f"{mode:04o}",
        "size_bytes": info.st_size,
    }


def validate_deployment(
    env_path: Path,
    *,
    expected_head: str,
    required_uid: int = 10001,
    require_secret_files: bool = True,
) -> dict[str, Any]:
    if not env_path.is_file():
        raise DeploymentPreflightError("deployment .env file is missing")
    values = parse_env(env_path)

    relay = _required(values, "SARA_RELAY_TOKEN")
    admin = _required(values, "SARA_ADMIN_TOKEN")
    for name, token in (("SARA_RELAY_TOKEN", relay), ("SARA_ADMIN_TOKEN", admin)):
        _reject_placeholder(name, token)
        if len(token) < 24:
            raise DeploymentPreflightError(f"{name} must contain at least 24 characters")
    if relay == admin:
        raise DeploymentPreflightError("SARA relay/admin tokens must be different")

    build_commit = _required(values, "SARA_BUILD_COMMIT").lower()
    if not _COMMIT.fullmatch(build_commit):
        raise DeploymentPreflightError("SARA_BUILD_COMMIT must be an exact 40-character SHA")
    if build_commit != expected_head.lower():
        raise DeploymentPreflightError(
            "SARA_BUILD_COMMIT does not match the checked-out Git HEAD"
        )

    release_id = _required(values, "SARA_RELEASE_ID")
    _reject_placeholder("SARA_RELEASE_ID", release_id)
    if not _IDENTIFIER.fullmatch(release_id):
        raise DeploymentPreflightError("SARA_RELEASE_ID is not a safe bounded identifier")

    prime_key_id = _required(values, "PRIME_SENTINEL_SIGNING_KEY_ID")
    _reject_placeholder("PRIME_SENTINEL_SIGNING_KEY_ID", prime_key_id)
    if not _IDENTIFIER.fullmatch(prime_key_id):
        raise DeploymentPreflightError(
            "PRIME_SENTINEL_SIGNING_KEY_ID is not a safe bounded identifier"
        )
    echo_key_id = _required(values, "ECHO_CHECKPOINT_KEY_ID")
    _reject_placeholder("ECHO_CHECKPOINT_KEY_ID", echo_key_id)
    if not _IDENTIFIER.fullmatch(echo_key_id):
        raise DeploymentPreflightError(
            "ECHO_CHECKPOINT_KEY_ID is not a safe bounded identifier"
        )

    signer_mode = values.get("ECHO_CHECKPOINT_SIGNER_MODE", "LOCAL_PEM").strip().upper()
    if signer_mode != "LOCAL_PEM":
        raise DeploymentPreflightError(
            "deployable localhost baseline requires ECHO_CHECKPOINT_SIGNER_MODE=LOCAL_PEM"
        )

    public_keys_raw = _required(values, "PRIME_SENTINEL_PUBLIC_KEYS_JSON")
    try:
        public_keys = json.loads(public_keys_raw)
    except json.JSONDecodeError as exc:
        raise DeploymentPreflightError(
            "PRIME_SENTINEL_PUBLIC_KEYS_JSON is not valid JSON"
        ) from exc
    if not isinstance(public_keys, dict) or prime_key_id not in public_keys:
        raise DeploymentPreflightError(
            "PRIME_SENTINEL_PUBLIC_KEYS_JSON must contain the configured signing key ID"
        )
    encoded_public = public_keys[prime_key_id]
    if not isinstance(encoded_public, str) or len(encoded_public) < 40:
        raise DeploymentPreflightError("configured PRIME public key is invalid")

    ports = {
        "sara": _port(values, "SARA_HOST_PORT", 9530),
        "prime_sentinel": _port(values, "PRIME_SENTINEL_HOST_PORT", 9540),
        "echo": _port(values, "ECHO_HOST_PORT", 9550),
    }
    if len(set(ports.values())) != len(ports):
        raise DeploymentPreflightError("SARA/PRIME/ECHO host ports must be distinct")

    files: dict[str, Any] = {}
    if require_secret_files:
        files = {
            name: _secret_file(values, name, required_uid=required_uid)
            for name in _SECRET_FILES
        }

    sanitized = {
        "build_commit": build_commit,
        "release_id": release_id,
        "prime_key_id": prime_key_id,
        "echo_key_id": echo_key_id,
        "echo_signer_mode": signer_mode,
        "ports": ports,
        "prime_public_key_ids": sorted(public_keys),
        "secret_files": files,
        "sara_tokens": {
            "relay": "PRESENT",
            "admin": "PRESENT",
            "independent": relay != admin,
        },
    }
    digest = hashlib.sha256(
        json.dumps(
            sanitized,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema": "WS-VERIFIED-LOCAL-FULL-STACK-PREFLIGHT-V1",
        "status": "PASS",
        **sanitized,
        "sanitized_config_sha256": digest,
        "claims_boundary": (
            "Host/configuration preflight for the localhost-only SARA/PRIME/ECHO "
            "deployment baseline. PASS does not establish external certification, "
            "HSM/KMS custody, public-network authorization, controlled-data approval, "
            "or independent validation."
        ),
    }


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".env")
    parser.add_argument("--expected-head", default=None)
    parser.add_argument("--required-uid", type=int, default=10001)
    parser.add_argument("--skip-secret-file-checks", action="store_true")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    receipt = validate_deployment(
        Path(args.env),
        expected_head=args.expected_head or _git_head(),
        required_uid=args.required_uid,
        require_secret_files=not args.skip_secret_file_checks,
    )
    encoded = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
