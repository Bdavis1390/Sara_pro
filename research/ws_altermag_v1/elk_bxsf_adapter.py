from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("numpy is required for the BXSF adapter") from exc


FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d*)?(?:[EeDd][-+]?\d+)?")
BAND_RE = re.compile(r"^\s*BAND\s*:\s*(\d+)\s*$", re.IGNORECASE)


def _f(token: str) -> float:
    return float(token.replace("D", "E").replace("d", "e"))


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_elk_task102(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    fermi = None
    for line in lines:
        if "fermi energy" in line.lower():
            toks = FLOAT_RE.findall(line)
            if toks:
                fermi = _f(toks[-1])
                break
    if fermi is None:
        raise ValueError("missing Fermi Energy")

    marker = next(
        (i for i, line in enumerate(lines) if line.strip().upper() == "BANDGRID_3D_BANDS"),
        None,
    )
    if marker is None:
        raise ValueError("missing BANDGRID_3D_BANDS")

    def next_nonempty(start: int) -> tuple[int, str]:
        for i in range(start, len(lines)):
            if lines[i].strip():
                return i, lines[i]
        raise ValueError("unexpected end of BXSF")

    i, line = next_nonempty(marker + 1)
    n_bands = int(FLOAT_RE.findall(line)[0])

    i, line = next_nonempty(i + 1)
    dims = tuple(int(round(_f(v))) for v in FLOAT_RE.findall(line)[:3])
    if len(dims) != 3 or min(dims) < 3:
        raise ValueError(f"invalid task-102 grid dimensions: {dims}")

    i, line = next_nonempty(i + 1)
    origin = tuple(_f(v) for v in FLOAT_RE.findall(line)[:3])

    recip = []
    for _ in range(3):
        i, line = next_nonempty(i + 1)
        recip.append(tuple(_f(v) for v in FLOAT_RE.findall(line)[:3]))

    expected = dims[0] * dims[1] * dims[2]
    bands: list[dict] = []
    cursor = i + 1
    while cursor < len(lines) and len(bands) < n_bands:
        match = None
        while cursor < len(lines):
            match = BAND_RE.match(lines[cursor])
            if match:
                break
            cursor += 1
        if not match:
            break

        band_id = int(match.group(1))
        cursor += 1
        values: list[float] = []
        while cursor < len(lines):
            if BAND_RE.match(lines[cursor]) or lines[cursor].strip().upper().startswith("END_BANDGRID"):
                break
            values.extend(_f(tok) for tok in FLOAT_RE.findall(lines[cursor]))
            cursor += 1
            if len(values) >= expected:
                break

        if len(values) != expected:
            raise ValueError(
                f"band {band_id}: expected {expected} energies, found {len(values)}"
            )
        bands.append({"band_id": band_id, "energies_ha": np.asarray(values).reshape(dims)})

    if len(bands) != n_bands:
        raise ValueError(f"header says {n_bands} bands, parsed {len(bands)}")

    return {
        "fermi_energy_ha": fermi,
        "dims_with_periodic_endpoint": dims,
        "origin": origin,
        "reciprocal_with_2pi_bohr_inv": tuple(recip),
        "bands": bands,
    }


def _strip_periodic_endpoint(arr: "np.ndarray", atol: float = 1.0e-10) -> "np.ndarray":
    checks = (
        np.allclose(arr[-1, :, :], arr[0, :, :], atol=atol, rtol=0.0),
        np.allclose(arr[:, -1, :], arr[:, 0, :], atol=atol, rtol=0.0),
        np.allclose(arr[:, :, -1], arr[:, :, 0], atol=atol, rtol=0.0),
    )
    if not all(checks):
        raise ValueError(f"task-102 periodic endpoint check failed: {checks}")
    return arr[:-1, :-1, :-1]


def _write_single_band_general_grid(
    path: Path,
    *,
    energies_ryd: "np.ndarray",
    reciprocal_no_2pi_bohr_inv: tuple[tuple[float, float, float], ...],
    origin: tuple[float, float, float],
    fermi_energy_ryd: float,
) -> None:
    nx, ny, nz = energies_ryd.shape
    with path.open("w", encoding="utf-8") as fh:
        fh.write(" BEGIN_INFO\n")
        fh.write(f"   Fermi Energy: {fermi_energy_ryd:.12f}\n")
        fh.write(" END_INFO\n")
        fh.write(" BEGIN_BLOCK_BANDGRID_3D\n")
        fh.write(" band_energies\n")
        fh.write(" BEGIN_BANDGRID_3D_BANDS\n")
        fh.write(" 1\n")
        fh.write(f" {nx} {ny} {nz}\n")
        fh.write(" " + " ".join(f"{v:.12f}" for v in origin) + "\n")
        for vec in reciprocal_no_2pi_bohr_inv:
            fh.write(" " + " ".join(f"{v:.12f}" for v in vec) + "\n")
        fh.write(" BAND: 1\n")
        flat = energies_ryd.reshape(-1)
        for j in range(0, len(flat), 6):
            fh.write("  " + "  ".join(f"{v:.12E}" for v in flat[j:j+6]) + "\n")
        fh.write(" END_BANDGRID_3D\n")
        fh.write(" END_BLOCK_BANDGRID_3D\n")


def adapt_elk_task102(
    input_path: Path,
    output_dir: Path,
    *,
    spin_label: str,
) -> dict:
    parsed = parse_elk_task102(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    recip = tuple(
        tuple(float(v) / (2.0 * math.pi) for v in vec)
        for vec in parsed["reciprocal_with_2pi_bohr_inv"]
    )
    fermi_ryd = 2.0 * float(parsed["fermi_energy_ha"])

    outputs = []
    for band in parsed["bands"]:
        stripped = _strip_periodic_endpoint(band["energies_ha"])
        energies_ryd = 2.0 * stripped
        out = output_dir / f"{spin_label}_band_{band['band_id']:04d}.bxsf"
        _write_single_band_general_grid(
            out,
            energies_ryd=energies_ryd,
            reciprocal_no_2pi_bohr_inv=recip,
            origin=parsed["origin"],
            fermi_energy_ryd=fermi_ryd,
        )
        outputs.append(
            {
                "band_id": band["band_id"],
                "path": str(out),
                "sha256": _sha256(out),
                "dims": list(energies_ryd.shape),
            }
        )

    record = {
        "input": str(input_path),
        "input_sha256": _sha256(input_path),
        "spin_label": spin_label,
        "source_dims": list(parsed["dims_with_periodic_endpoint"]),
        "output_band_count": len(outputs),
        "outputs": outputs,
        "transforms": [
            "split_multiband_bxsf_to_single_band_files",
            "strip_task102_periodic_duplicate_endpoint_on_each_axis",
            "energy_hartree_to_rydberg_multiply_by_2",
            "reciprocal_vectors_remove_2pi_factor_divide_by_2pi",
        ],
        "validation_status": "ADAPTER_IMPLEMENTED_REQUIRES_REAL_ELK_OUTPUT_AND_PINNED_PYSKEAF_VALIDATION",
        "claim_boundary": (
            "This adapter implements the declared unit/layout transformations between Elk task 102 "
            "and SKEAF-style single-band General Grid BXSF. It is not accepted for physics use until "
            "validated on real Elk output and parsed by the pinned PAOFLOW PySKEAF reader."
        ),
    }
    record["adapter_digest"] = sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--spin-label", required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()

    result = adapt_elk_task102(args.input, args.output_dir, spin_label=args.spin_label)
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.receipt:
        args.receipt.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
