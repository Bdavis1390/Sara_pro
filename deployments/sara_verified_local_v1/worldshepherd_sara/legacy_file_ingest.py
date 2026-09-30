from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_SUFFIXES = {".txt", ".md", ".csv", ".json"}
ROW_KINDS = {"hardware_bom", "network_configuration", "cable_record"}


@dataclass(frozen=True)
class LoadedLegacyArtifact:
    artifact_id: str
    kind: str
    relative_path: str
    sha256: str
    size_bytes: int
    artifact: dict[str, Any]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_beneath(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"artifact path escapes corpus root: {relative_path}") from exc
    if not candidate.is_file():
        raise ValueError(f"artifact path is not a file: {relative_path}")
    return candidate


def _load_rows_from_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV artifact requires a header row")
    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append({str(key): value for key, value in row.items() if key is not None})
    return rows


def _load_json_payload(text: str) -> dict[str, Any] | list[Any]:
    value = json.loads(text)
    if not isinstance(value, (dict, list)):
        raise ValueError("JSON artifact must contain an object or array")
    return value


def load_file_backed_artifact(
    *,
    corpus_root: str | Path,
    spec: dict[str, Any],
) -> LoadedLegacyArtifact:
    root = Path(corpus_root).resolve()
    artifact_id = str(spec["artifact_id"])
    kind = str(spec["kind"])
    relative_path = str(spec["path"])
    source_path = _resolve_beneath(root, relative_path)
    suffix = source_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"unsupported artifact suffix {suffix!r}; supported={sorted(SUPPORTED_SUFFIXES)}"
        )

    data = source_path.read_bytes()
    digest = _sha256(data)
    expected_digest = spec.get("expected_sha256")
    if expected_digest is not None and str(expected_digest).lower() != digest:
        raise ValueError(
            f"artifact digest mismatch for {artifact_id}: expected={expected_digest} actual={digest}"
        )

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"artifact is not UTF-8 text: {relative_path}") from exc

    artifact: dict[str, Any] = {
        "artifact_id": artifact_id,
        "kind": kind,
        "source_path": relative_path,
        "source_sha256": digest,
        "source_size_bytes": len(data),
    }
    if "expected_support" in spec:
        artifact["expected_support"] = list(spec["expected_support"])

    if suffix in {".txt", ".md"}:
        artifact["content"] = text.strip()
    elif suffix == ".csv":
        artifact["rows"] = _load_rows_from_csv(text)
    elif suffix == ".json":
        payload = _load_json_payload(text)
        if isinstance(payload, list):
            artifact["rows"] = payload
        elif "rows" in payload:
            rows = payload["rows"]
            if not isinstance(rows, list):
                raise ValueError(f"JSON rows must be a list: {relative_path}")
            artifact["rows"] = rows
        elif "content" in payload:
            artifact["content"] = str(payload["content"])
        else:
            artifact["structured"] = payload

    if kind in ROW_KINDS and "rows" not in artifact:
        raise ValueError(f"artifact kind {kind!r} requires row-oriented source data")
    if kind == "technical_manual_excerpt" and "content" not in artifact:
        raise ValueError("technical_manual_excerpt requires text content")

    return LoadedLegacyArtifact(
        artifact_id=artifact_id,
        kind=kind,
        relative_path=relative_path,
        sha256=digest,
        size_bytes=len(data),
        artifact=artifact,
    )


def load_file_backed_corpus(manifest_path: str | Path) -> tuple[dict[str, Any], tuple[LoadedLegacyArtifact, ...]]:
    path = Path(manifest_path).resolve()
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("legacy corpus manifest must be a JSON object")
    specs = manifest.get("legacy_artifacts")
    if not isinstance(specs, list) or not specs:
        raise ValueError("legacy corpus manifest requires non-empty legacy_artifacts")

    seen: set[str] = set()
    loaded: list[LoadedLegacyArtifact] = []
    for raw_spec in specs:
        if not isinstance(raw_spec, dict):
            raise ValueError("legacy artifact spec must be an object")
        item = load_file_backed_artifact(corpus_root=path.parent, spec=raw_spec)
        if item.artifact_id in seen:
            raise ValueError(f"duplicate artifact_id: {item.artifact_id}")
        seen.add(item.artifact_id)
        loaded.append(item)

    return manifest, tuple(loaded)
