from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .elk_input_b000 import render_elk_template


ROOT = Path(__file__).resolve().parent
DEFAULT_MANIFEST = ROOT / "manifests" / "fermi_export_b000.json"


def render_fermi_export(
    *,
    species_path: str,
    np3d: tuple[int, int, int] = (43, 43, 28),
    rgkmax: float = 8.0,
) -> str:
    return render_elk_template(
        ngridk=np3d,
        rgkmax=rgkmax,
        species_path=species_path,
        tasks=(102,),
        plot3d_grid=np3d,
    )


def validate_contract(path: Path = DEFAULT_MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    elk = manifest["elk"]
    outputs = set(elk["expected_outputs_collinear"])
    passed = (
        int(elk["required_task"]) == 102
        and outputs == {"FERMISURF_UP.bxsf", "FERMISURF_DN.bxsf"}
        and manifest["prerequisites"]["state_out_required"] is True
        and manifest["prerequisites"]["state_out_sha256_required"] is True
        and manifest["quantum_oscillation_stage"]["grid_convergence_required"] is True
    )
    template = render_fermi_export(
        species_path="/var/tmp/ws-altermag-elk-cache/pkg/usr/share/elk-lapw/species/",
        np3d=tuple(elk["initial_np3d"]),
    )
    return {
        "program": manifest["program"],
        "benchmark": manifest["benchmark"],
        "contract_pass": passed,
        "task": elk["required_task"],
        "expected_outputs": sorted(outputs),
        "template_sha256": sha256(template.encode("utf-8")).hexdigest(),
        "quantum_oscillation_stage": manifest["quantum_oscillation_stage"]["status"],
        "claim_boundary": manifest["claim_boundary"],
    }


def main() -> None:
    print(json.dumps(validate_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
