from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
from statistics import median


POINT_RE = re.compile(
    r"(?m)^It\s+(?P<step>\d+)/(?P<total>\d+):[^\n]*?=\s*"
    r"(?P<frequency>[+\-\d.eE]+)\s+GHz"
)
GMRES_NONCONVERGED = "GMRES solver did NOT converge"
RESIDUAL_RE = re.compile(
    r"Linear solver did not converge,\s*"
    r"norm\(Ax-b\)/norm\(b\)\s*=\s*(?P<residual>[+\-\d.eE]+)"
)


def summarize_nonconvergence_log(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    points = list(POINT_RE.finditer(text))
    if not points:
        raise ValueError("No Palace frequency point markers found")
    total = int(points[0].group("total"))
    if any(int(p.group("total")) != total for p in points):
        raise ValueError("Inconsistent Palace frequency count")

    entries = []
    for index, point in enumerate(points):
        section = text[
            point.end(): points[index + 1].start() if index + 1 < len(points) else len(text)
        ]
        step = int(point.group("step"))
        value = float(point.group("frequency"))
        match = RESIDUAL_RE.search(section)
        nonconverged = GMRES_NONCONVERGED in section
        if nonconverged != bool(match):
            raise ValueError(
                f"Frequency step {step}: inconsistent GMRES warning and residual"
            )
        entries.append({
            "step": step,
            "frequency_GHz_log_rounded": value,
            "gmres_nonconverged": nonconverged,
            "relative_residual": float(match.group("residual")) if match else None,
        })

    steps = [p["step"] for p in entries]
    if len(steps) != len(set(steps)) or steps != list(range(1, len(steps) + 1)):
        raise ValueError("Non-contiguous or repeated Palace iteration indices")
    residuals = [p["relative_residual"] for p in entries
                 if p["relative_residual"] is not None]
    if any(not math.isfinite(v) or v < 0 for v in residuals):
        raise ValueError("Non-finite or negative residuals")
    ordered = sorted(residuals)

    return {
        "source_path": str(path),
        "source_sha256": sha256(raw).hexdigest(),
        "total_frequency_points_declared": total,
        "frequency_points_parsed": len(entries),
        "nonconverged_frequency_points": len(residuals),
        "residual_min": min(residuals) if residuals else None,
        "residual_median": median(residuals) if residuals else None,
        "residual_max": max(residuals) if residuals else None,
        "residual_p90_nearest_rank": (
            ordered[math.ceil(0.9 * len(ordered)) - 1] if ordered else None
        ),
        "threshold_counts_gt": {
            "1e-3": sum(r > 1e-3 for r in residuals),
            "1e-4": sum(r > 1e-4 for r in residuals),
            "1e-5": sum(r > 1e-5 for r in residuals),
            "1e-6": sum(r > 1e-6 for r in residuals),
        },
        "worst_twelve": sorted(
            (p for p in entries if p["relative_residual"] is not None),
            key=lambda p: p["relative_residual"], reverse=True,
        )[:12],
        "entries": entries,
        "decision": (
            "HOLD_SOLVER_NONCONVERGENCE_REVIEW"
            if residuals else "NO_RECORDED_NONCONVERGENCE"
        ),
        "claim_boundary": (
            "This is a diagnostic extraction of solver-reported relative residuals; "
            "it does not establish a physical error bound on S-parameters or accept "
            "a nonconverged solve. Frequency strings inherit the log's rounding."
        ),
    }


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("stdout", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    result = summarize_nonconvergence_log(args.stdout)
    data = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(".tmp")
        tmp.write_text(data, encoding="utf-8")
        tmp.replace(args.output)
    print(json.dumps(
        {k: v for k, v in result.items() if k != "entries"},
        indent=2, sort_keys=True,
    ))


if __name__ == "__main__":
    main()
