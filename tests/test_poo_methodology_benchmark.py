from dataclasses import replace

from security.poo.methodology_benchmark import (
    AssuranceProfile,
    TripleCheckEvidence,
    compare_profiles,
    evaluate_triple_check,
    modeled_current_practice_composite_profile,
    poo_v3_internal_profile,
)
from security.poo.ownership_guard import OwnershipEvidence, evaluate_ownership
from security.poo.coc_guard import COCEvidence, coc_digest


def modeled_account_authentication_baseline():
    return AssuranceProfile(
        name="modeled account-authentication baseline",
        dimensions={
            "identity_binding": True,
            "challenge_response_control": True,
            "freshness": True,
            "revocation": False,
            "custody_evidence_binding": False,
            "exact_coc_digest_binding": False,
            "provenance_binding": False,
            "ownership_lineage": False,
            "custody_lineage": False,
            "coupled_ownership_custody_lineage": False,
            "conflict_detection": False,
            "stale_writer_protection": False,
            "durable_audit_provenance": False,
            "human_approval_boundary": False,
            "legal_title_nonclaim": True,
            "standard_interoperability": True,
        },
    )


def valid_ownership():
    return OwnershipEvidence(
        asset_id="asset:exhaustive",
        claimant_id="claimant:exhaustive",
        title_reference="title:exhaustive",
        control_key_fingerprint="key:exhaustive",
        work_reference="work:exhaustive",
        concept_reference="concept:exhaustive",
        coc_reference="coc:exhaustive",
        stake_reference="stake:exhaustive",
        issued_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        asset_fingerprint_bound=True,
        claimant_identity_bound=True,
        title_or_provenance_bound=True,
        pow_verified=True,
        poc_concept_verified=True,
        coc_verified=True,
        pos_bond_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def valid_coc():
    return COCEvidence(
        asset_id="asset:exhaustive",
        claimant_id="claimant:exhaustive",
        control_key_fingerprint="key:exhaustive",
        custody_reference="custody:exhaustive",
        custody_point_reference="custody:point:exhaustive",
        challenge_reference="challenge:exhaustive",
        observed_at="2026-09-16T00:00:00Z",
        expires_at="2026-09-17T00:00:00Z",
        previous_coc_digest=None,
        asset_binding_verified=True,
        claimant_binding_verified=True,
        custody_or_control_verified=True,
        challenge_response_verified=True,
        custody_chain_verified=True,
        freshness_verified=True,
        not_revoked=True,
    )


def test_poo_is_stronger_only_on_explicit_selected_assurance_dimensions():
    selected = (
        "custody_evidence_binding",
        "exact_coc_digest_binding",
        "provenance_binding",
        "ownership_lineage",
        "custody_lineage",
        "coupled_ownership_custody_lineage",
        "conflict_detection",
        "stale_writer_protection",
        "durable_audit_provenance",
        "human_approval_boundary",
    )
    d = compare_profiles(
        poo_v3_internal_profile(),
        modeled_account_authentication_baseline(),
        selected_dimensions=selected,
    )
    assert d.stronger_on_selected_dimensions is True
    assert d.status == "STRONGER_ON_SELECTED_DIMENSIONS_ONLY"
    assert d.weaker_dimensions == ()
    assert d.global_superiority_established is False
    assert d.standards_compliance_established is False
    assert d.legal_superiority_established is False
    assert d.external_validation_established is False


def test_generous_current_practice_composite_limits_advantage_to_poo_specific_constructions():
    current = modeled_current_practice_composite_profile()
    d = compare_profiles(
        poo_v3_internal_profile(),
        current,
        selected_dimensions=(
            "custody_evidence_binding",
            "exact_coc_digest_binding",
            "custody_lineage",
            "coupled_ownership_custody_lineage",
            "conflict_detection",
            "stale_writer_protection",
        ),
    )
    assert d.stronger_on_selected_dimensions is True
    assert set(d.stronger_dimensions) == {
        "exact_coc_digest_binding",
        "coupled_ownership_custody_lineage",
    }
    assert set(d.equal_dimensions) == {
        "custody_evidence_binding",
        "custody_lineage",
        "conflict_detection",
        "stale_writer_protection",
    }
    assert d.weaker_dimensions == ()
    assert d.global_superiority_established is False


def test_current_practice_composite_is_stronger_on_maturity_and_recognition_dimensions():
    d = compare_profiles(
        poo_v3_internal_profile(),
        modeled_current_practice_composite_profile(),
        selected_dimensions=(
            "exact_coc_digest_binding",
            "standard_interoperability",
            "independent_implementation",
            "production_deployment",
            "legal_recognition",
        ),
    )
    assert d.stronger_on_selected_dimensions is False
    assert "exact_coc_digest_binding" in d.stronger_dimensions
    assert set(d.weaker_dimensions) == {
        "standard_interoperability",
        "independent_implementation",
        "production_deployment",
        "legal_recognition",
    }
    assert d.status == "MIXED_OR_WEAKER_ON_SELECTED_DIMENSIONS"
    assert d.global_superiority_established is False


def test_standard_interoperability_prevents_global_or_selected_superiority_claim():
    d = compare_profiles(
        poo_v3_internal_profile(),
        modeled_account_authentication_baseline(),
        selected_dimensions=("standard_interoperability", "custody_lineage"),
    )
    assert d.stronger_on_selected_dimensions is False
    assert "standard_interoperability" in d.weaker_dimensions
    assert d.status == "MIXED_OR_WEAKER_ON_SELECTED_DIMENSIONS"
    assert d.global_superiority_established is False


def test_triple_check_requires_all_three_internal_layers_and_still_is_not_external_validation():
    complete = evaluate_triple_check(
        TripleCheckEvidence(
            protocol_regressions_passed=True,
            native_integration_regressions_passed=True,
            comparative_benchmark_passed=True,
        )
    )
    assert complete.internal_method_validation_complete is True
    assert complete.status == "INTERNAL_TRIPLE_CHECK_COMPLETE"
    assert complete.external_validation_established is False
    assert complete.global_superiority_established is False
    assert complete.production_readiness_established is False
    assert complete.legal_superiority_established is False

    for missing in (
        "protocol_regressions_passed",
        "native_integration_regressions_passed",
        "comparative_benchmark_passed",
    ):
        kwargs = {
            "protocol_regressions_passed": True,
            "native_integration_regressions_passed": True,
            "comparative_benchmark_passed": True,
        }
        kwargs[missing] = False
        d = evaluate_triple_check(TripleCheckEvidence(**kwargs))
        assert d.internal_method_validation_complete is False, missing


def test_every_boolean_combination_of_required_poo_predicates_is_fail_closed_except_all_true():
    fields = (
        "asset_fingerprint_bound",
        "claimant_identity_bound",
        "title_or_provenance_bound",
        "pow_verified",
        "poc_concept_verified",
        "coc_verified",
        "pos_bond_verified",
        "freshness_verified",
        "not_revoked",
    )
    base = valid_ownership()
    valid_count = 0
    for mask in range(1 << len(fields)):
        changes = {
            field: bool(mask & (1 << index))
            for index, field in enumerate(fields)
        }
        d = evaluate_ownership(replace(base, **changes))
        if all(changes.values()):
            assert d.poo_valid is True
            valid_count += 1
        else:
            assert d.poo_valid is False
            assert d.missing_predicates
    assert valid_count == 1


def test_coc_digest_commits_every_semantic_custody_field():
    base = valid_coc()
    original = coc_digest(base)
    mutations = {
        "asset_id": "asset:other",
        "claimant_id": "claimant:other",
        "control_key_fingerprint": "key:other",
        "custody_reference": "custody:other",
        "custody_point_reference": "custody:point:other",
        "challenge_reference": "challenge:other",
        "observed_at": "2026-09-16T00:00:01Z",
        "expires_at": "2026-09-18T00:00:00Z",
        "previous_coc_digest": "prior:coc",
    }
    for field, value in mutations.items():
        assert coc_digest(replace(base, **{field: value})) != original, field


def test_unknown_dimensions_are_rejected_instead_of_silently_scored():
    bad = AssuranceProfile(name="bad", dimensions={"imaginary_dimension": True})
    try:
        compare_profiles(
            bad,
            modeled_account_authentication_baseline(),
            selected_dimensions=("identity_binding",),
        )
    except ValueError as exc:
        assert "unknown assurance dimensions" in str(exc)
    else:
        raise AssertionError("unknown dimension should fail closed")
