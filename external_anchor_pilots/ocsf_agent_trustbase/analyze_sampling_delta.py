#!/usr/bin/env python3
"""
Provisional declared-vs-observed sampling/configuration delta analyzer for OCSF #1724.

This tool reports differences without deciding whether they are good, bad,
allowed, or sufficient. That matches the #1724 design principle: the producer
is a witness; relying-party policy supplies the verdict.

Missing values stay distinguishable from explicit values. The analyzer never
fills defaults.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MISSING = object()


def diff(declared, observed, path="$"):
    output = []

    if isinstance(declared, dict) or isinstance(observed, dict):
        declared_dict = declared if isinstance(declared, dict) else {}
        observed_dict = observed if isinstance(observed, dict) else {}

        for key in sorted(set(declared_dict) | set(observed_dict)):
            declared_value = declared_dict.get(key, MISSING)
            observed_value = observed_dict.get(key, MISSING)
            child_path = f"{path}.{key}"

            if declared_value is MISSING:
                output.append(
                    {
                        "path": child_path,
                        "state": "observed_only",
                        "declared": "<missing>",
                        "observed": observed_value,
                    }
                )
            elif observed_value is MISSING:
                output.append(
                    {
                        "path": child_path,
                        "state": "declared_only",
                        "declared": declared_value,
                        "observed": "<missing>",
                    }
                )
            else:
                output.extend(diff(declared_value, observed_value, child_path))
        return output

    if declared != observed:
        output.append(
            {
                "path": path,
                "state": "changed",
                "declared": declared,
                "observed": observed,
            }
        )

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cases = json.loads(args.fixture.read_text()).get("cases", [])
    if not cases:
        raise SystemExit("fixture must contain non-empty 'cases' list")

    results = []
    for case in cases:
        declared = case.get("declared", {})
        observed = case.get("observed", {})
        if not isinstance(declared, dict) or not isinstance(observed, dict):
            raise SystemExit("declared and observed must both be objects")

        differences = diff(declared, observed)
        results.append(
            {
                "name": case.get("name", "<unnamed>"),
                "changed": bool(differences),
                "difference_count": len(differences),
                "differences": differences,
            }
        )

    if args.json:
        print(json.dumps({"results": results}, indent=2))
    else:
        for result in results:
            marker = "DELTA" if result["changed"] else "STABLE"
            print(
                f"[{marker}] {result['name']}: "
                f"{result['difference_count']} difference(s)"
            )
            for item in result["differences"]:
                print(
                    f"  - {item['path']}: {item['state']} :: "
                    f"{item['declared']!r} -> {item['observed']!r}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
