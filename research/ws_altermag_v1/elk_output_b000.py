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


def _parse_numeric_line(line: str) -> list[float]:
    values = []
    for token in line.strip().split():
        try:
            values.append(_as_float(token))
        except ValueError:
            return []
    return values


def parse_scalar_series(text: str) -> list[float]:
    values = []
    for line in text.splitlines():
        row = _parse_numeric_line(line)
        if len(row) == 1:
            values.append(row[0])
    return values


def parse_vector_series(text: str) -> list[list[float]]:
    values = []
    for line in text.splitlines():
        row = _parse_numeric_line(line)
        if 1 <= len(row) <= 3:
            values.append(row)
    return values


def _vector_magnitude(values: list[float] | tuple[float, ...]) -> float:
    return math.sqrt(sum(float(v) ** 2 for v in values))


def parse_last_moments_block(text: str) -> dict | None:
    starts = [m.start() for m in re.finditer(r"^\s*Moments\s*:\s*$", text, flags=re.IGNORECASE | re.MULTILINE)]
    if not starts:
        return None

    block = text[starts[-1]:]
    species: dict[str, dict] = {}
    current_symbol: str | None = None
    interstitial = None
    total_muffin = None
    total_moment = None

    for line in block.splitlines()[1:]:
        m = re.match(rf"^\s*interstitial\s*:\s*((?:{FLOAT}\s*){{1,3}})\s*$", line, flags=re.IGNORECASE)
        if m:
            interstitial = [_as_float(v) for v in re.findall(FLOAT, m.group(1))]
            continue

        m = re.match(r"^\s*species\s*:\s*(\d+)\s*\(([^)]+)\)\s*$", line, flags=re.IGNORECASE)
        if m:
            current_symbol = m.group(2).strip()
            species.setdefault(current_symbol, {"species_index": int(m.group(1)), "atoms": {}})
            continue

        m = re.match(rf"^\s*atom\s+(\d+)\s*:\s*((?:{FLOAT}\s*){{1,3}})\s*$", line, flags=re.IGNORECASE)
        if m and current_symbol is not None:
            vec = [_as_float(v) for v in re.findall(FLOAT, m.group(2))]
            species[current_symbol]["atoms"][m.group(1)] = {
                "components_muB": vec,
                "magnitude_muB": _vector_magnitude(vec),
            }
            continue

        m = re.match(rf"^\s*total in muffin-tins\s*:\s*((?:{FLOAT}\s*){{1,3}})\s*$", line, flags=re.IGNORECASE)
        if m:
            total_muffin = [_as_float(v) for v in re.findall(FLOAT, m.group(1))]
            continue

        m = re.match(rf"^\s*total moment\s*:\s*((?:{FLOAT}\s*){{1,3}})\s*$", line, flags=re.IGNORECASE)
        if m:
            total_moment = [_as_float(v) for v in re.findall(FLOAT, m.group(1))]
            break

    return {
        "interstitial_muB": interstitial,
        "species": species,
        "total_muffin_tins_muB": total_muffin,
        "total_moment_muB": total_moment,
        "total_moment_magnitude_muB": (
            _vector_magnitude(total_moment) if total_moment is not None else None
        ),
    }


def parse_info_out(text: str) -> dict:
    total_energy = _last_match(
        [
            rf"^\s*({FLOAT})\s*:\s*total energy per unit cell\s*$",
            rf"^\s*total energy\s*:\s*({FLOAT})\s*$",
            rf"^\s*total energy\s+({FLOAT})\s*$",
        ],
        text,
    )

    moments = parse_last_moments_block(text)
    total_moment = moments["total_moment_muB"] if moments else None
    magnitude = moments["total_moment_magnitude_muB"] if moments else None
    if magnitude is None:
        magnitude = _last_match(
            [rf"Calculated total moment magnitude\s*:\s*({FLOAT})"],
            text,
        )

    convergence_change = _last_match(
        [rf"Absolute change in total energy \(target\)\s*:\s*({FLOAT})"],
        text,
    )

    cr_atoms = []
    if moments:
        cr_atoms = list(moments["species"].get("Cr", {}).get("atoms", {}).values())

    return {
        "total_energy_ha_per_cell": total_energy,
        "total_moment_muB": total_moment,
        "total_moment_magnitude_muB": magnitude,
        "energy_change_ha": convergence_change,
        "energy_convergence_target_achieved": "Energy convergence target achieved" in text,
        "moments": moments,
        "cr_local_moment_magnitudes_muB": [a["magnitude_muB"] for a in cr_atoms],
    }


def parse_momentm_out(text: str) -> dict:
    values = parse_scalar_series(text)
    return {
        "iteration_count": len(values),
        "values_muB": values,
        "final_total_moment_magnitude_muB": values[-1] if values else None,
    }


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize_run(run_dir: Path) -> dict:
    info_path = run_dir / "INFO.OUT"
    total_energy_path = run_dir / "TOTENERGY.OUT"
    dtotal_energy_path = run_dir / "DTOTENERGY.OUT"
    moment_path = run_dir / "MOMENT.OUT"
    momentm_path = run_dir / "MOMENTM.OUT"

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
    energies = (
        parse_scalar_series(total_energy_path.read_text(encoding="utf-8", errors="replace"))
        if total_energy_path.exists()
        else []
    )
    energy_changes = (
        parse_scalar_series(dtotal_energy_path.read_text(encoding="utf-8", errors="replace"))
        if dtotal_energy_path.exists()
        else []
    )
    moment_vectors = (
        parse_vector_series(moment_path.read_text(encoding="utf-8", errors="replace"))
        if moment_path.exists()
        else []
    )
    momentm = (
        parse_momentm_out(momentm_path.read_text(encoding="utf-8", errors="replace"))
        if momentm_path.exists()
        else None
    )

    final_energy = energies[-1] if energies else (info["total_energy_ha_per_cell"] if info else None)
    final_moment = moment_vectors[-1] if moment_vectors else (info["total_moment_muB"] if info else None)
    final_moment_mag = (
        momentm["final_total_moment_magnitude_muB"]
        if momentm is not None and momentm["final_total_moment_magnitude_muB"] is not None
        else (_vector_magnitude(final_moment) if final_moment else None)
    )

    return {
        "run_dir": str(run_dir),
        "final_total_energy_ha_per_cell": final_energy,
        "final_energy_change_ha": energy_changes[-1] if energy_changes else (info["energy_change_ha"] if info else None),
        "final_total_moment_muB": final_moment,
        "final_total_moment_magnitude_muB": final_moment_mag,
        "cr_local_moment_magnitudes_muB": info["cr_local_moment_magnitudes_muB"] if info else [],
        "energy_convergence_target_achieved": info["energy_convergence_target_achieved"] if info else False,
        "scf_iteration_count_from_energy_file": len(energies),
        "info_out_exists": info_path.exists(),
        "totenergy_out_exists": total_energy_path.exists(),
        "moment_out_exists": moment_path.exists(),
        "momentm_out_exists": momentm_path.exists(),
        "info": info,
        "outputs": outputs,
        "parse_complete_enough_for_energy_gate": final_energy is not None,
        "parse_complete_enough_for_moment_gate": bool(
            info and info["cr_local_moment_magnitudes_muB"]
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
