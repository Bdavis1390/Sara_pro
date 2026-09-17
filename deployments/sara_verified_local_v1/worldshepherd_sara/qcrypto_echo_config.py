from __future__ import annotations

import hmac
import os
import stat
from pathlib import Path
from urllib.parse import urlsplit

from .qcrypto_echo_forwarder import QCryptoEchoForwarder, QCryptoEchoForwarderError


ECHO_PERSISTENCE_URL_ENV = "ECHO_PERSISTENCE_URL"
ECHO_FORWARD_TOKEN_FILE_ENV = "ECHO_FORWARD_TOKEN_FILE"
LOCAL_HTTP_HOSTS = frozenset({"echo", "localhost", "127.0.0.1", "::1"})
MAX_TOKEN_BYTES = 4096
MIN_TOKEN_CHARS = 32


def _validated_url(raw: str) -> str:
    if not raw or len(raw) > 512:
        raise QCryptoEchoForwarderError("ECHO persistence URL is missing or too long")
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise QCryptoEchoForwarderError("ECHO persistence URL must use http or https")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise QCryptoEchoForwarderError("ECHO persistence URL contains forbidden components")
    if parsed.path not in {"", "/"}:
        raise QCryptoEchoForwarderError("ECHO persistence URL must not contain an application path")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HTTP_HOSTS:
        raise QCryptoEchoForwarderError("cleartext ECHO forwarding is restricted to the local deployment")
    return raw.rstrip("/")


def _read_token(path_value: str) -> str:
    path = Path(path_value)
    if not path_value or not path.is_absolute():
        raise QCryptoEchoForwarderError(f"{ECHO_FORWARD_TOKEN_FILE_ENV} must be an absolute path")
    try:
        link_status = path.lstat()
    except OSError as exc:
        raise QCryptoEchoForwarderError("unable to inspect ECHO forward-token file") from exc
    if stat.S_ISLNK(link_status.st_mode):
        raise QCryptoEchoForwarderError("ECHO forward-token file must not be a symbolic link")
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        status = os.fstat(descriptor)
        if not stat.S_ISREG(status.st_mode):
            raise QCryptoEchoForwarderError("ECHO forward-token file must be a regular file")
        if (status.st_dev, status.st_ino) != (link_status.st_dev, link_status.st_ino):
            raise QCryptoEchoForwarderError("ECHO forward-token file changed during secure open")
        if status.st_uid != os.geteuid() or stat.S_IMODE(status.st_mode) & 0o077:
            raise QCryptoEchoForwarderError("ECHO forward-token file ownership or mode is unsafe")
        if status.st_size < 1 or status.st_size > MAX_TOKEN_BYTES:
            raise QCryptoEchoForwarderError("ECHO forward-token file size is invalid")
        data = os.read(descriptor, MAX_TOKEN_BYTES + 1)
    except OSError as exc:
        raise QCryptoEchoForwarderError("unable to read ECHO forward-token file") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(data) > MAX_TOKEN_BYTES:
        raise QCryptoEchoForwarderError("ECHO forward-token file is too large")
    try:
        token = data.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError as exc:
        raise QCryptoEchoForwarderError("ECHO forward-token file must be UTF-8") from exc
    if len(token) < MIN_TOKEN_CHARS or token != token.strip() or "\n" in token or "\r" in token:
        raise QCryptoEchoForwarderError("ECHO forward-token file must contain one strong token")
    for name in ("SARA_ADMIN_TOKEN", "SARA_RELAY_TOKEN", "PRIME_SENTINEL_SERVICE_TOKEN"):
        other = os.getenv(name, "")
        if other and hmac.compare_digest(token, other):
            raise QCryptoEchoForwarderError(f"ECHO forwarding credential must be independent from {name}")
    return token


def forwarder_from_environment() -> QCryptoEchoForwarder | None:
    raw_url = os.getenv(ECHO_PERSISTENCE_URL_ENV, "").strip()
    raw_file = os.getenv(ECHO_FORWARD_TOKEN_FILE_ENV, "").strip()
    if not raw_url and not raw_file:
        return None
    if not raw_url or not raw_file:
        raise QCryptoEchoForwarderError("ECHO forwarding configuration is incomplete")
    return QCryptoEchoForwarder(base_url=_validated_url(raw_url), token=_read_token(raw_file))
