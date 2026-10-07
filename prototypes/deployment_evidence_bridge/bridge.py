#!/usr/bin/env python3
"""Operator-supplied deployment/SBOM evidence bridge. No live observation or certification."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

SCHEMA = "ws-deployment-evidence-bridge-poc-v0.2"
MAX_INPUT_BYTES = 10_000_000
MAX_DEPLOYMENTS = 1_000
MAX_COMPONENTS = 10_000
MAX_FINDINGS = 10_000
MAX_FIELD_CHARS = 2_048
MAX_OBSERVATION_AGE = timedelta(hours=24)
MAX_CLOCK_SKEW = timedelta(minutes=5)
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_FIELDS = ("application", "environment", "cluster", "namespace", "gitops_revision",
           "canonical_project_url", "desired_image_digest")
_CSV_FIELDS = ("application", "environment", "cluster", "namespace", "gitops_revision",
               "canonical_project_url", "reported_alignment", "observation_freshness",
               "component", "version", "purl", "sbom_sha256", "vulnerability_status",
               "regulatory_status", "record_id")


def digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def load_bytes(path: Path) -> bytes:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds 10 MB limit: " + path.name)
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds 10 MB limit: " + path.name)
    return data


def read_json_bytes(data: bytes, label: str) -> dict:
    try:
        result = json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid JSON: " + label) from exc
    if not isinstance(result, dict):
        raise ValueError("JSON document must be an object: " + label)
    return result


def relative_file(root: Path, filename: str) -> Path:
    if not isinstance(filename, str) or not filename or len(filename) > MAX_FIELD_CHARS:
        raise ValueError("Referenced file path must be a nonempty bounded string")
    target = (root / filename).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError("Referenced file must exist inside input directory: " + filename)
    return target


def require_text(doc: dict, key: str) -> str:
    value = doc.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_FIELD_CHARS:
        raise ValueError("Missing or invalid deployment field: " + key)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("Control character not permitted: " + key)
    return value


def sha256_field(value: str | None, label: str, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError("Invalid " + label + "; expected sha256:<64 lowercase hex>")


def utc_time(value: str, label: str) -> datetime:
    if not isinstance(value, str) or len(value) > 45:
        raise ValueError("Invalid " + label + "; expected RFC3339 timestamp with UTC offset")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid " + label) from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timezone required for " + label)
    return result.astimezone(timezone.utc)


def project_url(value: str) -> None:
    try:
        parts = urlsplit(value)
        host = parts.hostname
        _ = parts.port
    except ValueError as exc:
        raise ValueError("Malformed canonical_project_url") from exc
    if (parts.scheme != "https" or not host or not parts.netloc or
            parts.username is not None or parts.password is not None or
            parts.query or parts.fragment or any(ch.isspace() for ch in value)):
        raise ValueError("canonical_project_url must be absolute HTTPS without credentials/query/fragment")


def csv_safe(value):
    """Prevent spreadsheet formula execution when the CSV is opened interactively."""
    if value is None:
        return ""
    value = str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def normalize(root: Path, manifest: dict, now: str):
    if not isinstance(manifest, dict):
        raise ValueError("Top-level manifest must be a JSON object")
    deployments = manifest.get("deployments")
    if not isinstance(deployments, list) or len(deployments) > MAX_DEPLOYMENTS:
        raise ValueError("deployments must be a list of at most 1000 records")
    now_utc = utc_time(now, "generated_at")
    records, export_rows = [], []
    seen = set()
    source_digests = {}
    for d in deployments:
        if not isinstance(d, dict):
            raise ValueError("Deployment records must be objects")
        for field in _FIELDS:
            require_text(d, field)
        project_url(d["canonical_project_url"])
        sha256_field(d["desired_image_digest"], "desired_image_digest")
        key = tuple(d[field] for field in _FIELDS[:4])
        if key in seen:
            raise ValueError("Duplicate deployment key: " + repr(key))
        seen.add(key)

        observed = d.get("observed_image_digest")
        sha256_field(observed, "observed_image_digest", optional=True)
        source = d.get("observation_source")
        observed_at = d.get("observed_at")
        if observed is None and (source is not None or observed_at is not None):
            raise ValueError("Observation metadata supplied without observed_image_digest")
        freshness = "NOT_OBSERVED"
        observed_age_seconds = None
        if observed is not None:
            require_text(d, "observation_source")
            observed_utc = utc_time(observed_at, "observed_at")
            if observed_utc > now_utc + MAX_CLOCK_SKEW:
                raise ValueError("observed_at is implausibly in the future")
            age = now_utc - observed_utc
            observed_age_seconds = max(0, int(age.total_seconds()))
            freshness = "STALE_REPORTED" if age > MAX_OBSERVATION_AGE else "RECENT_REPORTED"
        alignment = ("UNVERIFIED" if observed is None else
                     "MATCH_REPORTED" if observed == d["desired_image_digest"] else "DRIFT_REPORTED")

        sbom_file = d.get("sbom_file")
        components, sbom_sha = [], None
        if sbom_file is not None:
            sbom_path = relative_file(root, sbom_file)
            raw = load_bytes(sbom_path)
            sbom_sha = digest(raw)
            source_digests[sbom_path.relative_to(root.resolve()).as_posix()] = sbom_sha
            sbom = read_json_bytes(raw, sbom_file)
            contents = sbom.get("components", [])
            if (sbom.get("bomFormat") != "CycloneDX" or
                    not isinstance(sbom.get("specVersion"), str) or
                    not isinstance(contents, list) or len(contents) > MAX_COMPONENTS):
                raise ValueError("Malformed or oversized CycloneDX document: " + sbom_file)
            for c in contents:
                if not isinstance(c, dict) or not isinstance(c.get("name"), str) or not c["name"]:
                    raise ValueError("CycloneDX component must have a name")
                components.append({name: c.get(original) for name, original in
                                   (("name", "name"), ("version", "version"),
                                    ("purl", "purl"), ("bom_ref", "bom-ref"))})

        findings_file = d.get("findings_file")
        finding_count = 0
        findings_sha = None
        if findings_file is not None:
            findings_path = relative_file(root, findings_file)
            raw = load_bytes(findings_path)
            findings_sha = digest(raw)
            source_digests[findings_path.relative_to(root.resolve()).as_posix()] = findings_sha
            finding_doc = read_json_bytes(raw, findings_file)
            findings = finding_doc.get("findings")
            if (finding_doc.get("schema") != "SOURCE_PROVIDED_FINDINGS_V1" or
                    not isinstance(findings, list) or len(findings) > MAX_FINDINGS):
                raise ValueError("Unsupported or oversized supplied findings")
            finding_count = len(findings)

        rid = digest(json.dumps(key, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        record = {
            "record_id": rid,
            **{field: d[field] for field in _FIELDS},
            "reported_observation": {
                "image_digest": observed, "source": source, "at": observed_at,
                "alignment": alignment, "freshness": freshness,
                "age_seconds": observed_age_seconds,
                "independently_verified": False,
            },
            "sbom_file": sbom_file, "sbom_sha256": sbom_sha,
            "component_count": len(components), "components": components,
            # Do not copy raw, operator-supplied findings into an unreviewed evidence export.
            "findings_sha256": findings_sha, "finding_count": finding_count,
            "vulnerability_status": "SOURCE_PROVIDED_UNVALIDATED" if findings_file is not None else "NOT_EVALUATED",
            "vex_status": "NOT_EVALUATED",
            "regulatory_status": "NO_COMPLIANCE_DETERMINATION",
            "evidence_gap": [name for name, missing in (
                ("observed_runtime_state", observed is None),
                ("fresh_runtime_report", freshness != "RECENT_REPORTED"),
                ("sbom_attachment", sbom_file is None),
                ("vulnerability_findings", findings_file is None),
                ("independent_observation_validation", True),
                ("compliance_assessment", True),
            ) if missing],
        }
        records.append(record)
        for component in components or [{"name": None, "version": None, "purl": None}]:
            export_rows.append({
                "application": d["application"], "environment": d["environment"],
                "cluster": d["cluster"], "namespace": d["namespace"],
                "gitops_revision": d["gitops_revision"],
                "canonical_project_url": d["canonical_project_url"],
                "reported_alignment": alignment,
                "observation_freshness": freshness,
                "component": component["name"], "version": component["version"],
                "purl": component["purl"], "sbom_sha256": sbom_sha,
                "vulnerability_status": record["vulnerability_status"],
                "regulatory_status": record["regulatory_status"], "record_id": rid,
            })

    return ({"schema": SCHEMA, "generated_at_utc": now_utc.isoformat(),
             "limits": [
                 "All inputs are operator-provided; nothing is independently authenticated.",
                 "A matching reported digest is not a runtime attestation.",
                 "Timestamp checks assess claimed freshness, not source authenticity.",
                 "SBOM completeness, vulnerability findings, VEX and NIS2/ISMS compliance are not certified.",
             ],
             "source_digests": source_digests, "deployments": records}, export_rows)


def atomic_write_text(path: Path, content: str) -> None:
    """Replace each output file atomically, with no temporary files left behind."""
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         delete=False, newline="") as stream:
            tmp = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def build(input_path: Path, output_path: Path, *, now: str | None = None) -> None:
    input_path = input_path.resolve()
    root = input_path.parent
    raw = load_bytes(input_path)
    manifest = read_json_bytes(raw, input_path.name)
    now = now or datetime.now(timezone.utc).isoformat()
    payload, rows = normalize(root, manifest, now)
    payload["source_digests"][input_path.name] = digest(raw)
    out_json = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    buff = io.StringIO(newline="")
    writer = csv.DictWriter(buff, fieldnames=_CSV_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: csv_safe(row.get(key)) for key in _CSV_FIELDS})
    output_path.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output_path / "deployment_evidence.json", out_json)
    atomic_write_text(output_path / "inventory_evidence.csv", buff.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Operator-supplied deployment snapshot")
    parser.add_argument("--out", required=True, type=Path, help="Evidence output directory")
    args = parser.parse_args()
    build(args.input, args.out)


if __name__ == "__main__":
    main()
