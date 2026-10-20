#!/usr/bin/env python3
"""Read-only Palace campaign evidence inventory. Standard library only."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def analyze_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        n = 0
        freq = []
        nonfinite = {}
        for row in reader:
            n += 1
            for name in columns:
                value = (row.get(name) or "").strip()
                try:
                    x = float(value)
                except (ValueError, TypeError):
                    continue
                if not math.isfinite(x):
                    nonfinite[name] = nonfinite.get(name, 0) + 1
                elif "frequency" in name.lower() or name.strip().lower().startswith("f ("):
                    freq.append(x)
    return {"rows": n, "columns": columns, "frequency_min": min(freq) if freq else None,
            "frequency_max": max(freq) if freq else None, "nonfinite_by_column": nonfinite}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path, help="Existing campaign root; never modified")
    parser.add_argument("--output", type=Path, help="Write report to separate path")
    args = parser.parse_args()
    root = args.campaign.resolve(strict=True)
    results = []
    for directory in sorted((root / "work").glob("A0*")):
        if not directory.is_dir():
            continue
        files = []
        for name in ("port-S.csv", "port-floquet-S.csv", "port-I.csv", "port-V.csv", "domain-E.csv", "error-indicators.csv"):
            matches = sorted(directory.rglob(name))
            for path in matches:
                entry = {"path": str(path.relative_to(root)), "bytes": path.stat().st_size,
                         "sha256": digest(path)}
                try:
                    entry["csv"] = analyze_csv(path)
                except (OSError, UnicodeError, csv.Error) as exc:
                    entry["parse_error"] = str(exc)
                files.append(entry)
        results.append({"case": directory.name, "files": files})
    report = {"schema": "worldshepherd.palace.inventory.v1",
              "warning": "Inventory only. No convergence, passivity, power balance, or physical validation implied.",
              "campaign": str(root), "cases": results}
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        out = args.output.expanduser().resolve()
        if out == root or root in out.parents:
            parser.error("--output must be outside the campaign tree")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

if __name__ == "__main__":
    main()
