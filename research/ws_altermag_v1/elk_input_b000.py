from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path

from .structure_b000 import DEFAULT_STRUCTURE


ANGSTROM_TO_BOHR = 1.8897261246257702
DEFAULT_BFIELD_AU = 1.0e-3


def render_elk_template(
    structure_path: Path = DEFAULT_STRUCTURE,
    *,
    bfield_au: float = DEFAULT_BFIELD_AU,
    ngridk: tuple[int, int, int] = (43, 43, 28),
    rgkmax: float | None = None,
    species_path: str = "/usr/share/elk-lapw/species/",
) -> str:
    data = json.loads(structure_path.read_text(encoding="utf-8"))
    lattice = data["lattice_A"]
    a_bohr = float(lattice["a"]) * ANGSTROM_TO_BOHR
    c_over_a = float(lattice["c"]) / float(lattice["a"])

    sites = {s["label"]: s for s in data["sites"]}

    def pos(label: str, field_z: float) -> str:
        p = sites[label]["fractional"]
        return (
            f"  {p[0]:.16f} {p[1]:.16f} {p[2]:.16f} "
            f"0.0 0.0 {field_z:.8e}"
        )

    lines = [
        "! WS-ALTERMAG B000 Elk cross-check template",
        "! NOT EXECUTION APPROVED: run only after resource/convergence/provenance gates clear.",
        "! PBE GGA uses Elk xctype=20; local Cr bfcmt values only seed opposite spin symmetry.",
        "",
        "tasks",
        "  0",
        "",
        "xctype",
        "  20",
        "",
        "spinpol",
        "  .true.",
        "",
        "scale",
        f"  {a_bohr:.16f}",
        "",
        "avec",
        "  1.0 0.0 0.0",
        f"  -0.5 {math.sqrt(3.0)/2.0:.16f} 0.0",
        f"  0.0 0.0 {c_over_a:.16f}",
        "",
        "sppath",
        f"  '{species_path}'",
        "",
        "atoms",
        "  2",
        "  'Cr.in'",
        "  2",
        pos("Cr1", +bfield_au),
        pos("Cr2", -bfield_au),
        "  'Sb.in'",
        "  2",
        pos("Sb1", 0.0),
        pos("Sb2", 0.0),
        "",
        "reducebf",
        "  0.5",
        "",
    ]

    if rgkmax is not None:
        lines.extend([
            "rgkmax",
            f"  {float(rgkmax):.6f}",
            "",
        ])

    lines.extend([
        "ngridk",
        f"  {int(ngridk[0])} {int(ngridk[1])} {int(ngridk[2])}",
        "",
        "! Mandatory before execution:",
        "! 1. verify installed Elk/package/species hashes against backend_selection_b000.json",
        "! 2. run k-grid, rgkmax and energy convergence controls",
        "! 3. verify the symmetry-breaking field magnitude does not change converged observables",
        "! 4. preserve INFO.OUT and all relevant outputs in an ECHO provenance receipt",
        "",
    ])
    return "\n".join(lines)


def template_digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--kgrid", nargs=3, type=int, default=(43, 43, 28))
    parser.add_argument("--rgkmax", type=float)
    args = parser.parse_args()
    text = render_elk_template(ngridk=tuple(args.kgrid), rgkmax=args.rgkmax)
    if args.output:
        if args.output.name == "elk.in":
            raise SystemExit("refusing to write executable-named elk.in before execution gate clearance")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    print(f"! TEMPLATE_SHA256 {template_digest(text)}")


if __name__ == "__main__":
    main()
