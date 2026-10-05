from __future__ import annotations

import json
from pathlib import Path

from .schema import digest


ROOT = Path(__file__).resolve().parent
DEFAULT_DFT_MANIFEST = ROOT / "manifests" / "crsb_dft_b000.json"


REQUIRED_REFERENCE_FIELDS = (
    "code",
    "basis",
    "exchange_correlation",
    "k_mesh",
    "lattice_A",
    "parent_space_group",
    "magnetic_symmetry_model",
    "magnetic_initialization",
    "fermi_surface_frequency_tool",
    "band_alignment_eV",
)


def validate_contract(path: Path = DEFAULT_DFT_MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    reference = manifest["reference_method"]
    missing = [field for field in REQUIRED_REFERENCE_FIELDS if field not in reference]

    kmesh_ok = reference.get("k_mesh") == [43, 43, 28]
    lattice = reference.get("lattice_A", {})
    lattice_ok = (
        lattice.get("a") == 4.12
        and lattice.get("b") == 4.12
        and lattice.get("c") == 5.47
    )
    shifts = reference.get("band_alignment_eV", {})
    shifts_ok = (
        shifts.get("dogbone_hole_sheets") == -0.11
        and shifts.get("web_electron_sheets") == 0.015
    )

    gate = manifest["execution_gate"]
    required_gates_declared = all(
        key in gate
        for key in (
            "requires_backend_present",
            "requires_input_structure_hash",
            "requires_solver_version",
            "requires_solver_binary_hash",
            "requires_atomic_positions_verified",
            "requires_kmesh_convergence",
            "requires_energy_convergence",
            "requires_resource_clearance",
        )
    )

    execution_deferred = (
        manifest["execution_status"] == "PROPOSED_NOT_EXECUTED"
        and gate["current_resource_clearance"] is False
    )

    complete = (
        not missing
        and kmesh_ok
        and lattice_ok
        and shifts_ok
        and required_gates_declared
        and execution_deferred
    )

    record = {
        "program": manifest["program"],
        "benchmark": manifest["benchmark"],
        "contract_complete": complete,
        "missing_reference_fields": missing,
        "kmesh_ok": kmesh_ok,
        "lattice_ok": lattice_ok,
        "band_alignment_ok": shifts_ok,
        "execution_status": manifest["execution_status"],
        "resource_clearance": gate["current_resource_clearance"],
        "current_blocker": gate["current_blocker"],
        "claim_status": ["IMPLEMENTED IN SOFTWARE", "SUPPORTED BY LITERATURE"],
        "claim_boundary": (
            "This validates the DFT reproduction contract only. No first-principles CrSb calculation "
            "has been executed by this node, and no DFT physics result is claimed."
        ),
    }
    record["contract_digest"] = digest(record)
    return record


def main() -> None:
    print(json.dumps(validate_contract(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
