from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Iterable


FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?"


def _as_float(value: str) -> float:
    return float(value.replace("D", "E").replace("d", "e"))


def _last_match(patterns: Iterable[str], text: str) -> float | None:
    found: list[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            found.append(_as_float(match.group(1)))
    return found[-1] if found else None


def parse_info_out(text: str) -> dict:
    total_energy = _last_match(
        [
            rf"^\s*({FLOAT})\s*:\s*total energy per unit cell\s*$",
            rf"^\s*total energy\s*:\s*({FLOAT})\s*$",
            rf"^\s*total energy\s+({FLOAT})\s*$",
        ],
        text,
    )

    moment_vectors = []
    for match in re.finditer(
        rf"^\s*total moment\s*:\s*({FLOAT})\s+({FLOAT})\s+({FLOAT})\s*$",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        vec = tuple(_as_float(match.group(i)) for i in (1, 2, 3))
        moment_vectors.append(vec)

    total_moment = moment_vectors[-1] if moment_vectors else None
    magnitude = (
        math.sqrt(sum(v * v for v in total_moment))
        if total_moment is not None
        else _last_match(
            [rf"Calculated total moment magnitude\s*:\s*({FLOAT})"],
            text,
        )
    )

    convergence_target = _last_match(
        [rf"Absolute change in total energy \(target\)\s*:\s*({FLOAT})"],
        text,
    )

    return {
        "total_energy_ha_per_cell": total_energy,
        "total_moment_muB": total_moment,
        "total_moment_magnitude_muB": magnitude,
        "energy_change_reported": convergence_target,
    }


def parse_momentm_out(text: str) -> dict:
    """Preserve numeric MOMENTM.OUT rows without assuming undocumented column semantics."""
    rows: list[list[float]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = stripped.split()
        values = []
        try:
            values = [_as_float(tok) for tok in tokens]
        except ValueError:
            continue
        if values:
            rows.append(values)

    return {
        "numeric_row_count": len(rows),
        "last_numeric_row": rows[-1] if rows else None,
        "rows": rows,
        "semantics": "RAW_NUMERIC_ONLY_PENDING_FIRST_REAL_OUTPUT_FORMAT_CONFIRMATION",
    }


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize_run(run_dir: Path) -> dict:
    info_path = run_dir / "INFO.OUT"
    moment_path = run_dir / "MOMENTM.OUT"

    outputs = {}
    for path in sorted(p for p in run_dir.iterdir() if p.is_file()):
        outputs[path.name] = {
            "size": path.stat().st_size,
            "sha256": _sha256(path),
        }

    info = (
        parse_info_out(info_path.read_text(encoding="utf-8", errors="replace"))
        if info_path.exists()
        else None
    )
    moment = (
        parse_momentm_out(moment_path.read_text(encoding="utf-8", errors="replace"))
        if moment_path.exists()
        else None
    )

    return {
        "run_dir": str(run_dir),
        "info_out_exists": info_path.exists(),
        "momentm_out_exists": moment_path.exists(),
        "info": info,
        "momentm": moment,
        "outputs": outputs,
        "parse_complete_enough_for_energy_gate": bool(
            info is not None and info["total_energy_ha_per_cell"] is not None
        ),
        "claim_boundary": (
            "Output parsing is an evidence extraction step. Parsed values are not a convergence "
            "or physical-validation claim until the declared cross-run gates evaluate them."
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = summarize_run(args.run_dir)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
