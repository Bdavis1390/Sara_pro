"""Repository-level cryptographic surface discovery for PQC migration planning.

This scanner is deliberately conservative: it finds code/configuration references
that deserve review. A finding does not prove that the named primitive or protocol
is deployed in production.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
from typing import Iterable


@dataclass(frozen=True)
class CryptoFinding:
    path: str
    line: int
    category: str
    token: str
    severity: str
    interpretation: str


_PATTERNS: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "classical_public_key",
        re.compile(r"\b(RSA|ECDSA|Ed25519|X25519|DSA|secp256k1|secp256r1)\b", re.IGNORECASE),
        "migration_review",
        "Public-key use may require PQ or hybrid migration depending on the protocol and retention horizon.",
    ),
    (
        "protocol_surface",
        re.compile(r"\b(TLS|SSL|SSH|OIDC|JWT|OpenID|mTLS)\b", re.IGNORECASE),
        "inventory",
        "Protocol reference requires deployed-suite and implementation discovery before PQ readiness can be assessed.",
    ),
    (
        "symmetric_or_hash",
        re.compile(r"\b(AES(?:-?\d+)?|SHA-?(?:1|224|256|384|512)|SHA3|HMAC|BLAKE2|BLAKE3)\b", re.IGNORECASE),
        "inventory",
        "Symmetric/hash primitives are not replaced one-for-one by PQ public-key standards; retain for algorithm inventory and parameter review.",
    ),
    (
        "pqc_standard",
        re.compile(r"\b(ML-KEM|ML-DSA|SLH-DSA|FIPS\s*203|FIPS\s*204|FIPS\s*205)\b", re.IGNORECASE),
        "informational",
        "Post-quantum standard reference detected.",
    ),
    (
        "credential_surface",
        re.compile(r"\b(api[_-]?key|access[_-]?token|bearer|client[_-]?secret|private[_-]?key)\b", re.IGNORECASE),
        "secrets_review",
        "Credential-handling reference detected; verify secret-store injection and non-persistence in evidence/logs.",
    ),
    (
        "private_key_material",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "critical",
        "Private-key material appears to be present in repository text and must be investigated immediately.",
    ),
)

_TEXT_SUFFIXES = {
    ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sh", ".bash", ".txt", ".env", ".example", ".qasm",
}
_IGNORE_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
_IGNORE_PATHS = {
    "worldshepherd_sara/pqc_inventory.py",
    "tests/test_pqc_inventory.py",
    "data/pqc_migration_inventory.json",
}


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in _IGNORE_DIRS for part in relative.parts):
            continue
        if relative.as_posix() in _IGNORE_PATHS:
            continue
        if path.stat().st_size > 1_000_000:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES and path.name not in {"Dockerfile", ".env.example"}:
            continue
        yield path


def scan_repository(root: str | Path) -> dict[str, object]:
    base = Path(root).resolve()
    findings: list[CryptoFinding] = []
    files_scanned = 0

    for path in _iter_text_files(base):
        files_scanned += 1
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = path.relative_to(base).as_posix()
        for line_number, line in enumerate(lines, start=1):
            for category, pattern, severity, interpretation in _PATTERNS:
                for match in pattern.finditer(line):
                    findings.append(
                        CryptoFinding(
                            path=rel,
                            line=line_number,
                            category=category,
                            token=match.group(0),
                            severity=severity,
                            interpretation=interpretation,
                        )
                    )

    findings.sort(key=lambda row: (row.path, row.line, row.category, row.token.lower()))
    summary: dict[str, int] = {}
    for row in findings:
        summary[row.category] = summary.get(row.category, 0) + 1

    critical = [row for row in findings if row.severity == "critical"]
    return {
        "schema_version": "1.0",
        "status": "CRITICAL_REVIEW_REQUIRED" if critical else "DISCOVERY_COMPLETE_REVIEW_REQUIRED",
        "files_scanned": files_scanned,
        "finding_count": len(findings),
        "summary": dict(sorted(summary.items())),
        "critical_count": len(critical),
        "findings": [asdict(row) for row in findings],
        "claim_control": "Findings are repository references, not proof of deployed cryptographic configuration.",
    }


def write_inventory(report: dict[str, object], output_path: str | Path) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
