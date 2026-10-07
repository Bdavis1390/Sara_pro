from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re


EV_PER_RYDBERG = 13.605693122994
ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "manifests" / "band_alignment_b000.json"
FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d*)?(?:[EeDd][-+]?\d+)?")


def ev_to_rydberg(ev: float) -> float:
    return float(ev) / EV_PER_RYDBERG


def declared_shift_rydberg(sheet_class: str, path: Path = DEFAULT_MANIFEST) -> float:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if sheet_class not in manifest["transforms"]:
        raise ValueError(f"undeclared sheet class: {sheet_class}")
    return ev_to_rydberg(float(manifest["transforms"][sheet_class]["shift_eV"]))


def _sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def shift_single_band_bxsf(
    input_path: Path,
    output_path: Path,
    *,
    sheet_class: str,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    shift_ev = float(manifest["transforms"][sheet_class]["shift_eV"])
    shift_ry = ev_to_rydberg(shift_ev)

    lines = input_path.read_text(encoding="utf-8").splitlines()
    if sum(1 for line in lines if line.strip().upper().startswith("BAND:")) != 1:
        raise ValueError("band alignment requires a single-band BXSF")

    in_data = False
    out_lines: list[str] = []
    shifted_count = 0
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("BAND:"):
            in_data = True
            out_lines.append(line)
            continue
        if in_data and stripped.upper().startswith("END_BANDGRID"):
            in_data = False
            out_lines.append(line)
            continue
        if in_data:
            toks = stripped.split()
            vals = []
            try:
                vals = [float(tok.replace("D", "E").replace("d", "e")) for tok in toks]
            except ValueError:
                out_lines.append(line)
                continue
            if vals:
                out_lines.append("  " + "  ".join(f"{v + shift_ry:.12E}" for v in vals))
                shifted_count += len(vals)
                continue
        out_lines.append(line)

    if shifted_count == 0:
        raise ValueError("no band-energy values shifted")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {
        "input": str(input_path),
        "input_sha256": _sha256(input_path),
        "output": str(output_path),
        "output_sha256": _sha256(output_path),
        "sheet_class": sheet_class,
        "shift_eV": shift_ev,
        "shift_Ry": shift_ry,
        "shifted_energy_count": shifted_count,
        "raw_preserved": input_path.resolve() != output_path.resolve(),
        "lane": "ALIGNED",
        "claim_boundary": manifest["claim_boundary"],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sheet-class", required=True)
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        raise SystemExit("refusing to overwrite raw BXSF")
    result = shift_single_band_bxsf(
        args.input,
        args.output,
        sheet_class=args.sheet_class,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
