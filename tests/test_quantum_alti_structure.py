from dataclasses import replace
from pathlib import Path

from worldshepherd_sara.quantum_alti_structure import (
    PeriodicStructureFreezeRecord,
    ReferenceComputationRecord,
    StructureFormat,
    StructureSourceType,
    sha256_text,
    structure_file_digest,
    structure_template_as_dict,
    validate_reference_computation,
    validate_structure_freeze,
)


SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def _structure(path: Path) -> PeriodicStructureFreezeRecord:
    return PeriodicStructureFreezeRecord(
        project_id="WS-ALTI",
        structure_id="WS-ALTI-FIXTURE-L12-001",
        composition="Al3Sc",
        phase_label="L12 software fixture",
        structure_format=StructureFormat.CIF,
        structure_digest=structure_file_digest(path),
        source_type=StructureSourceType.WORLD_SHEPHERD_GENERATED,
        source_reference="synthetic-test-fixture://WS-ALTI-FIXTURE-L12-001",
        source_reference_digest=sha256_text("synthetic-test-fixture metadata"),
        periodicity=3,
        space_group="Pm-3m fixture",
        lattice_a_angstrom=4.1,
        lattice_b_angstrom=4.1,
        lattice_c_angstrom=4.1,
        alpha_deg=90.0,
        beta_deg=90.0,
        gamma_deg=90.0,
        atom_count=4,
        species_counts={"Al": 3, "Sc": 1},
        site_ordering_digest=sha256_text("fixture-sites:Sc@0,0,0;Al@0,.5,.5;Al@.5,0,.5;Al@.5,.5,0"),
        modeling_scope="software fixture for validator unit test; not WS-AlTi physical evidence",
        generated_from_composition_only=False,
    )


def test_structure_freeze_requires_actual_matching_periodic_file(tmp_path):
    path = tmp_path / "fixture.cif"
    path.write_text("data_fixture\n_cell_length_a 4.1\n", encoding="utf-8")
    record = _structure(path)

    missing_file = validate_structure_freeze(record)
    assert missing_file.accepted is False
    assert any("actual structure file is required" in reason for reason in missing_file.reasons)

    accepted = validate_structure_freeze(record, structure_file=path)
    assert accepted.accepted is True
    assert accepted.gate_id == "WS-ALTI-EXT-01"
    assert accepted.precondition_id == "WS-ALTI-P0-PHYSICAL-STRUCTURE-FROZEN"


def test_composition_only_model_is_rejected_even_if_digest_exists(tmp_path):
    path = tmp_path / "fixture.cif"
    path.write_text("data_fixture\n", encoding="utf-8")
    record = replace(_structure(path), generated_from_composition_only=True)

    decision = validate_structure_freeze(record, structure_file=path)
    assert decision.accepted is False
    assert any("composition-only" in reason for reason in decision.reasons)


def test_placeholder_or_wrong_digest_is_rejected(tmp_path):
    path = tmp_path / "fixture.cif"
    path.write_text("data_fixture\n", encoding="utf-8")
    record = replace(_structure(path), structure_id="<replace-me>", structure_digest=SHA_A)

    decision = validate_structure_freeze(record, structure_file=path)
    assert decision.accepted is False
    assert any("structure_id" in reason for reason in decision.reasons)
    assert any("does not match" in reason for reason in decision.reasons)


def test_site_counts_and_lattice_are_checked(tmp_path):
    path = tmp_path / "fixture.cif"
    path.write_text("data_fixture\n", encoding="utf-8")
    record = replace(
        _structure(path),
        atom_count=5,
        lattice_a_angstrom=0.0,
        alpha_deg=180.0,
    )

    decision = validate_structure_freeze(record, structure_file=path)
    assert decision.accepted is False
    assert any("sum to atom_count" in reason for reason in decision.reasons)
    assert any("lattice_a_angstrom" in reason for reason in decision.reasons)
    assert any("alpha_deg" in reason for reason in decision.reasons)


def test_reference_computation_must_bind_to_exact_frozen_structure(tmp_path):
    path = tmp_path / "fixture.cif"
    path.write_text("data_fixture\n", encoding="utf-8")
    structure = _structure(path)
    record = ReferenceComputationRecord(
        project_id="WS-ALTI",
        structure_id=structure.structure_id,
        structure_digest=structure.structure_digest,
        computation_id="WS-ALTI-DFT-FIXTURE-001",
        code_name="fixture-code",
        code_version="1.0",
        method="Kohn-Sham DFT fixture",
        exchange_correlation="PBE fixture",
        basis_or_pseudopotential="fixture PAW description",
        kpoint_definition="4x4x4 fixture mesh",
        spin_treatment="non-spin-polarized fixture",
        convergence_energy_ev=1e-6,
        convergence_force_ev_per_angstrom=1e-3,
        input_digest=SHA_A,
        output_digest=SHA_B,
        total_energy_ev=-10.0,
        reference_kind="software validator fixture",
        source_reference="synthetic-test-fixture://WS-ALTI-DFT-FIXTURE-001",
    )

    accepted = validate_reference_computation(record, frozen_structure=structure)
    assert accepted.accepted is True

    mismatched = validate_reference_computation(
        replace(record, structure_digest=SHA_A),
        frozen_structure=structure,
    )
    assert mismatched.accepted is False
    assert any("not bound" in reason for reason in mismatched.reasons)


def test_acquisition_template_is_deliberately_incomplete_and_not_evidence():
    payload = structure_template_as_dict()
    assert payload["gate_id"] == "WS-ALTI-EXT-01"
    assert payload["record"]["structure_id"] == "<replace-me>"
    assert "Template only" in payload["claim_control"]
