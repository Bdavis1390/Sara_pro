"""WS-QBENCH-MGRAPH v0.10 Code S1 ingestion and provenance gate.

This utility does not execute untrusted MATLAB code. It inventories the expected
Code S1 source files, computes SHA-256 digests, and extracts implementation
markers relevant to the remaining reproduction discrepancy.

Exact reproduction remains fail-closed until the expected files are locally
present and this manifest has been reviewed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

EXPECTED_FILES = (
    "R003_Rabi_001_eig_Fock_data.m",
    "R003_Rabi_001_eig_Fock_post.m",
    "R003_Rabi_001_eig_Fock_post_plot.m",
)

MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    "factorial": re.compile(r"\bfactorial\s*\(", re.IGNORECASE),
    "gamma_family": re.compile(r"\b(?:gamma|gammaln)\s*\(", re.IGNORECASE),
    "laguerre": re.compile(r"\b(?:laguerreL|laguerre)\s*\(", re.IGNORECASE),
    "prod": re.compile(r"\bprod\s*\(", re.IGNORECASE),
    "randperm": re.compile(r"\brandperm\s*\(", re.IGNORECASE),
    "randi": re.compile(r"\brandi\s*\(", re.IGNORECASE),
    "datasample": re.compile(r"\bdatasample\s*\(", re.IGNORECASE),
    "exact_zero_test": re.compile(r"(?:==|~=)\s*0(?:\.0*)?\b"),
    "eps": re.compile(r"\beps\b", re.IGNORECASE),
    "realmin": re.compile(r"\brealmin\b", re.IGNORECASE),
    "single": re.compile(r"\bsingle\s*\(", re.IGNORECASE),
    "double": re.compile(r"\bdouble\s*\(", re.IGNORECASE),
    "symbolic": re.compile(r"\b(?:sym|vpa)\s*\(", re.IGNORECASE),
}


class CodeS1IngestError(RuntimeError):
    pass


@dataclass(frozen=True)
class MatlabSourceInventory:
    filename: str
    sha256: str
    bytes: int
    lines: int
    markers: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def sha256_file(path: str | Path) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def scan_matlab_text(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in MARKER_PATTERNS.items()}


def inventory_matlab_file(path: str | Path) -> MatlabSourceInventory:
    p = Path(path)
    if p.suffix.lower() != ".m":
        raise CodeS1IngestError(f"expected MATLAB .m file: {p.name}")
    raw = p.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return MatlabSourceInventory(
        filename=p.name,
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes=len(raw),
        lines=len(text.splitlines()),
        markers=scan_matlab_text(text),
    )


def inventory_code_s1(root: str | Path) -> dict[str, object]:
    root = Path(root)
    missing = [name for name in EXPECTED_FILES if not (root / name).is_file()]
    if missing:
        raise CodeS1IngestError("missing expected Code S1 files: " + ", ".join(missing))

    rows = [inventory_matlab_file(root / name) for name in EXPECTED_FILES]
    return {
        "schema": "ws-qbench-mgraph/code-s1-manifest-v0.10",
        "expected_files": list(EXPECTED_FILES),
        "files": [row.to_dict() for row in rows],
        "review_required": True,
        "execution_performed": False,
    }


def source_semantics_summary(manifest: dict[str, object]) -> dict[str, int]:
    totals = {name: 0 for name in MARKER_PATTERNS}
    for row in manifest.get("files", []):
        markers = row.get("markers", {})
        for name in totals:
            totals[name] += int(markers.get(name, 0))
    return totals


def write_manifest(root: str | Path, output: str | Path) -> dict[str, object]:
    manifest = inventory_code_s1(root)
    Path(output).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def require_reviewed_hash_lock(
    manifest: dict[str, object],
    reviewed_hashes: dict[str, str],
) -> None:
    """Fail unless each expected source hash matches a human-reviewed lock."""
    files = manifest.get("files", [])
    actual = {row["filename"]: row["sha256"] for row in files}
    for name in EXPECTED_FILES:
        expected = reviewed_hashes.get(name)
        if not expected:
            raise CodeS1IngestError(f"no reviewed SHA-256 lock for {name}")
        if actual.get(name) != expected:
            raise CodeS1IngestError(f"SHA-256 mismatch for {name}")


def candidate_zero_semantics_questions(manifest: dict[str, object]) -> list[str]:
    """Produce bounded review questions from observed source markers."""
    totals = source_semantics_summary(manifest)
    questions: list[str] = []
    if totals["factorial"]:
        questions.append("Inspect factorial evaluation for overflow/underflow at Nmax=200.")
    if totals["gamma_family"]:
        questions.append("Compare gamma/gammaln ratio evaluation against the stable log-gamma implementation.")
    if totals["laguerre"]:
        questions.append("Identify the exact Laguerre routine and numeric type used for l_nm.")
    if totals["prod"]:
        questions.append("Inspect the multiplication order used to form W_q and its float64 underflow behavior.")
    if totals["exact_zero_test"]:
        questions.append("Locate each exact zero/nonzero branch that affects loop connectivity.")
    if totals["single"]:
        questions.append("Verify whether any single-precision cast enters the hopping or W_q path.")
    if totals["realmin"] or totals["eps"]:
        questions.append("Record any explicit machine-precision constants affecting zero semantics.")
    if totals["randperm"] or totals["datasample"] or totals["randi"]:
        questions.append("Verify without-replacement subgraph sampling directly from the source.")
    return questions
