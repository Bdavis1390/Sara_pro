#!/usr/bin/env python3
"""Validate Worldshepherd/QCRYPTO SPDX-PQC proposal fixtures.

This validates local proposal evidence only. It does not establish SPDX acceptance,
cryptographic implementation validation, interoperability, or certification.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by runtime setup
    raise SystemExit("PyYAML is required: python -m pip install 'PyYAML>=6,<7'") from exc


EXPECTED = {
    "ML-KEM": {
        "standard": "FIPS-203",
        "variants": {"ML-KEM-512", "ML-KEM-768", "ML-KEM-1024"},
        "required_lengths": {
            "publicKeyLength",
            "privateKeyLength",
            "ciphertextLength",
            "sharedSecretLength",
        },
        "signature": False,
    },
    "ML-DSA": {
        "standard": "FIPS-204",
        "variants": {"ML-DSA-44", "ML-DSA-65", "ML-DSA-87"},
        "required_lengths": {"publicKeyLength", "privateKeyLength", "signatureLength"},
        "signature": True,
    },
    "SLH-DSA": {
        "standard": "FIPS-205",
        "variants": {
            f"SLH-DSA-{family}-{level}{profile}"
            for family in ("SHA2", "SHAKE")
            for level in ("128", "192", "256")
            for profile in ("s", "f")
        },
        "required_lengths": {"publicKeyLength", "signatureLength"},
        "signature": True,
    },
}

FALSE_CLAIM_FIELDS = (
    "implementationValidated",
    "sideChannelValidated",
    "interoperabilityValidated",
)


def load_fixture(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level YAML value must be a mapping")
    return data


def validate_fixture(data: dict[str, Any], source: str = "<memory>") -> list[str]:
    errors: list[str] = []
    algorithm = data.get("algorithm")
    spec = EXPECTED.get(algorithm)
    if spec is None:
        return [f"{source}: unsupported algorithm {algorithm!r}"]

    standard = data.get("standard")
    if not isinstance(standard, dict):
        errors.append(f"{source}: standard must be a mapping")
    else:
        if standard.get("authority") != "NIST":
            errors.append(f"{source}: standard.authority must be NIST")
        if standard.get("id") != spec["standard"]:
            errors.append(
                f"{source}: standard.id must be {spec['standard']}, got {standard.get('id')!r}"
            )
        if standard.get("status") != "final":
            errors.append(f"{source}: standard.status must remain final")

    variants = data.get("variants")
    if not isinstance(variants, list) or not variants:
        errors.append(f"{source}: variants must be a non-empty list")
        return errors

    ids: list[str] = []
    for index, variant in enumerate(variants):
        where = f"{source}: variants[{index}]"
        if not isinstance(variant, dict):
            errors.append(f"{where}: variant must be a mapping")
            continue
        variant_id = variant.get("id")
        if not isinstance(variant_id, str) or not variant_id:
            errors.append(f"{where}: id must be a non-empty string")
        else:
            ids.append(variant_id)

        category = variant.get("nistSecurityCategory")
        if category not in {1, 2, 3, 5}:
            errors.append(f"{where}: invalid NIST security category {category!r}")

        lengths = variant.get("lengths")
        if not isinstance(lengths, dict):
            errors.append(f"{where}: lengths must be a mapping")
        else:
            missing = set(spec["required_lengths"]) - set(lengths)
            if missing:
                errors.append(f"{where}: missing length fields {sorted(missing)}")
            for name, length in lengths.items():
                lwhere = f"{where}.lengths.{name}"
                if not isinstance(length, dict):
                    errors.append(f"{lwhere}: length record must be a mapping")
                    continue
                source_value = length.get("sourceValue")
                normalized_value = length.get("normalizedValue")
                if not isinstance(source_value, int) or source_value <= 0:
                    errors.append(f"{lwhere}: sourceValue must be a positive integer")
                if length.get("sourceUnit") != "bytes":
                    errors.append(f"{lwhere}: sourceUnit must be bytes")
                if length.get("normalizedUnit") != "bits":
                    errors.append(f"{lwhere}: normalizedUnit must be bits")
                if isinstance(source_value, int) and normalized_value != source_value * 8:
                    errors.append(
                        f"{lwhere}: normalizedValue must equal sourceValue*8 "
                        f"({source_value * 8}), got {normalized_value!r}"
                    )

        if spec["signature"]:
            modes = variant.get("signingMode")
            if not isinstance(modes, list) or set(modes) != {"deterministic", "hedged"}:
                errors.append(
                    f"{where}: signingMode must contain exactly deterministic and hedged"
                )

        if algorithm == "SLH-DSA":
            if variant.get("digestFamily") not in {"SHA2", "SHAKE"}:
                errors.append(f"{where}: digestFamily must be SHA2 or SHAKE")
            if variant.get("profile") not in {"small-signature", "fast-signing"}:
                errors.append(f"{where}: invalid SLH-DSA profile")

    if len(ids) != len(set(ids)):
        errors.append(f"{source}: duplicate variant ids detected")
    expected_ids = set(spec["variants"])
    if set(ids) != expected_ids:
        missing = sorted(expected_ids - set(ids))
        extra = sorted(set(ids) - expected_ids)
        errors.append(f"{source}: variant set mismatch; missing={missing}, extra={extra}")

    validation = data.get("validation")
    if not isinstance(validation, dict):
        errors.append(f"{source}: validation must be a mapping")
    else:
        if validation.get("relationshipPreserved") is not True:
            errors.append(f"{source}: validation.relationshipPreserved must be true")
        for field in FALSE_CLAIM_FIELDS:
            if validation.get(field) is not False:
                errors.append(f"{source}: validation.{field} must remain false")

    return errors


def validate_directory(fixtures_dir: Path) -> list[str]:
    errors: list[str] = []
    files = sorted(fixtures_dir.glob("*.yaml"))
    if len(files) != len(EXPECTED):
        errors.append(
            f"{fixtures_dir}: expected {len(EXPECTED)} YAML fixtures, found {len(files)}"
        )
    seen_algorithms: set[str] = set()
    for path in files:
        data = load_fixture(path)
        algorithm = data.get("algorithm")
        if isinstance(algorithm, str):
            seen_algorithms.add(algorithm)
        errors.extend(validate_fixture(data, str(path)))
    if seen_algorithms != set(EXPECTED):
        errors.append(
            f"{fixtures_dir}: algorithm set mismatch; expected={sorted(EXPECTED)}, "
            f"found={sorted(seen_algorithms)}"
        )
    return errors


def _default_fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "docs" / "qcrypto" / "spdx-pqc" / "fixtures"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixtures_dir", nargs="?", type=Path, default=_default_fixture_dir())
    args = parser.parse_args()
    errors = validate_directory(args.fixtures_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: validated SPDX-PQC proposal fixtures in {args.fixtures_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
