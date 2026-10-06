from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path


EXPECTED_COLUMNS = (
    "Azimuthal(deg)",
    "Polar(deg)",
    "Freq(kT)",
    "mstar(me)",
    "Curv(kTA2)",
    "Type(+e-h)",
    "NumOrbCopy",
)


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_freqvsangle(path: Path) -> dict:
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        raise ValueError("empty PySKEAF frequency output")

    header = [cell.strip() for cell in rows[0]]
    if tuple(header) != EXPECTED_COLUMNS:
        raise ValueError(f"unexpected PySKEAF freqvsangle header: {header}")

    out = []
    for lineno, row in enumerate(rows[1:], start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) != len(EXPECTED_COLUMNS):
            raise ValueError(f"line {lineno}: expected 7 columns, found {len(row)}")
        try:
            values = [float(c.strip()) for c in row]
        except ValueError as exc:
            raise ValueError(f"line {lineno}: non-numeric PySKEAF result") from exc
        out.append({
            # Preserve PySKEAF writer order rather than relabeling the historical headings.
            "writer_theta_deg": values[0],
            "writer_phi_deg": values[1],
            "frequency_kT": values[2],
            "effective_mass_me": values[3],
            "curvature_kT_A2": values[4],
            "orbit_type": values[5],
            "num_orbit_copies": int(round(values[6])),
        })

    return {
        "source": str(path),
        "source_sha256": _sha256(path),
        "row_count": len(out),
        "orbits": out,
        "claim_boundary": (
            "This parser preserves frequencies and writer-angle fields from the pinned PySKEAF "
            "freqvsangle format. It does not classify Fermi-surface sheets or select dogbone orbits."
        ),
    }


def validate_selection_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(data["allowed_sheet_classes"])
    required = set(data["required_fields"])
    errors = []
    seen = set()

    for index, item in enumerate(data["assignments"]):
        missing = sorted(required - set(item))
        if missing:
            errors.append({"index": index, "error": "MISSING_FIELDS", "fields": missing})
            continue
        if item["sheet_class"] not in allowed:
            errors.append({"index": index, "error": "INVALID_SHEET_CLASS"})
        key = (item["spin"], int(item["band_id"]))
        if key in seen:
            errors.append({"index": index, "error": "DUPLICATE_SPIN_BAND"})
        seen.add(key)
        if len(str(item["source_bxsf_sha256"])) != 64:
            errors.append({"index": index, "error": "INVALID_SOURCE_HASH"})

    dogbone = [
        item for item in data["assignments"]
        if item.get("sheet_class") == "dogbone_hole"
    ]
    dogbone_ready = len(dogbone) >= 2 and not errors

    return {
        "status": data["status"],
        "assignment_count": len(data["assignments"]),
        "dogbone_assignment_count": len(dogbone),
        "errors": errors,
        "dogbone_ready": dogbone_ready,
        "decision": "ALLOW_DOGBONE_QO_SELECTION" if dogbone_ready else "BLOCK_DOGBONE_QO_SELECTION",
        "claim_boundary": data["claim_boundary"],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--freqvsangle", type=Path)
    parser.add_argument("--selection-manifest", type=Path)
    args = parser.parse_args()

    if bool(args.freqvsangle) == bool(args.selection_manifest):
        raise SystemExit("provide exactly one of --freqvsangle or --selection-manifest")

    result = (
        parse_freqvsangle(args.freqvsangle)
        if args.freqvsangle
        else validate_selection_manifest(args.selection_manifest)
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
