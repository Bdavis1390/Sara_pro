"""Source-integrity and dependency allowlist gate for the QCRYPTO package."""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class SourceIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceIntegrityPolicy:
    allowed_external_import_roots: tuple[str, ...] = ("cryptography", "boto3", "botocore")
    reject_untracked_python_files: bool = True

    @property
    def policy_sha256(self) -> str:
        body = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(b"WS-QCRYPTO-SOURCE-INTEGRITY-POLICY-V1\x00" + body).hexdigest()


def build_source_manifest(package_root: str | Path) -> dict:
    root = Path(package_root).resolve()
    if not root.is_dir():
        raise SourceIntegrityError("package_root must be a directory")
    files = {}
    for path in sorted(root.rglob("*.py")):
        if path.is_symlink() or not path.is_file():
            raise SourceIntegrityError("source manifest refuses symlink/non-file Python sources")
        rel = path.relative_to(root).as_posix()
        files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = {"schema": "WS-QCRYPTO-SOURCE-MANIFEST-V1", "files": files}
    payload["manifest_sha256"] = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def verify_source_manifest(package_root: str | Path, manifest: Mapping, *, policy: SourceIntegrityPolicy = SourceIntegrityPolicy()) -> dict:
    root = Path(package_root).resolve()
    claimed = dict(manifest.get("files") or {})
    if not claimed:
        raise SourceIntegrityError("source manifest contains no files")
    current = build_source_manifest(root)
    errors: list[str] = []
    for rel, expected in sorted(claimed.items()):
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise SourceIntegrityError("source manifest path escapes package root") from exc
        if not path.is_file() or path.is_symlink():
            errors.append(f"MISSING_OR_SYMLINK:{rel}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"HASH_MISMATCH:{rel}")
    if policy.reject_untracked_python_files:
        extra = sorted(set(current["files"]) - set(claimed))
        errors.extend(f"UNTRACKED:{x}" for x in extra)

    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    allowed_external = set(policy.allowed_external_import_roots)
    dependency_edges: dict[str, list[str]] = {}
    for rel in sorted(claimed):
        path = root / rel
        if not path.is_file():
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except Exception as exc:
            errors.append(f"AST_PARSE_ERROR:{rel}")
            continue
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    imports.add("worldshepherd_qcrypto_kms")
                elif node.module:
                    imports.add(node.module.split(".")[0])
        dependency_edges[rel] = sorted(imports)
        for imp in imports:
            if imp == "worldshepherd_qcrypto_kms" or imp in stdlib or imp in allowed_external:
                continue
            errors.append(f"UNAPPROVED_IMPORT:{rel}:{imp}")
    return {
        "schema": "WS-QCRYPTO-SOURCE-INTEGRITY-REPORT-V1",
        "manifest_sha256": manifest.get("manifest_sha256"),
        "current_manifest_sha256": current["manifest_sha256"],
        "policy_sha256": policy.policy_sha256,
        "dependency_edges": dependency_edges,
        "errors": errors,
        "satisfied": not errors,
    }
