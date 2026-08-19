from __future__ import annotations

from worldshepherd_sara.integrations.promotion import (
    REQUIRED_EVIDENCE_CATEGORIES,
    assess_promotion_readiness,
)


def test_incomplete_package_is_not_ready_and_never_auto_promotes():
    result = assess_promotion_readiness(
        surface="isaac_sim_ros2",
        submitted_claim_status="REQUIRES_LAB_VALIDATION",
        evidence_by_category={
            "runtime_version_inventory": ["evidence://versions/001"],
            "configuration_digest": ["evidence://config/001"],
        },
    )

    assert result.ready_for_human_review is False
    assert result.auto_promotion_allowed is False
    assert result.decision == "INCOMPLETE_EVIDENCE_PACKAGE"
    assert "operator_authorization" in result.missing_categories


def test_complete_package_only_becomes_ready_for_human_review():
    package = {
        category: [f"evidence://{category}/001"]
        for category in REQUIRED_EVIDENCE_CATEGORIES
    }

    result = assess_promotion_readiness(
        surface="omniverse_kit",
        submitted_claim_status="REQUIRES_PARTNER_VALIDATION",
        evidence_by_category=package,
    )

    assert result.ready_for_human_review is True
    assert result.auto_promotion_allowed is False
    assert result.missing_categories == ()
    assert result.evidence_ref_count == len(REQUIRED_EVIDENCE_CATEGORIES)
    assert result.decision == "READY_FOR_HUMAN_REVIEW"
    assert result.submitted_claim_status == "REQUIRES_PARTNER_VALIDATION"
