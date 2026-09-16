"""Worldshepherd mapping for Federal PQC migration functions.

This module maps public Federal migration requirements to Worldshepherd
components for planning and gap analysis. It does not assert Federal compliance,
certification, procurement qualification, or government approval.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlMapping:
    requirement_id: str
    requirement: str
    modules: tuple[str, ...]
    evidence_target: str
    status: str = "DESIGN_MAPPING"


MAPPINGS = (
    ControlMapping(
        "OMB-M26-15-GOV",
        "Establish or update agency-wide PQC governance, roles, accountability, and migration ownership.",
        ("SARA", "PRIME"),
        "Approved migration workflow, named owners, approval gates, and auditable decisions.",
    ),
    ControlMapping(
        "OMB-M26-15-PLAN",
        "Maintain a dynamic multi-year PQC migration plan and phased execution record.",
        ("SARA", "ECHO", "OVERWATCH"),
        "Versioned plan, phase state, milestone evidence, deviations, and status history.",
    ),
    ControlMapping(
        "OMB-M26-15-RISK",
        "Prioritize migration based on system impact, high-value assets, sensitive data, and exposure risk.",
        ("SARA", "PRIME", "OVERWATCH"),
        "Risk-ranked backlog with human-approved priority and documented rationale.",
    ),
    ControlMapping(
        "OMB-M26-15-INVENTORY",
        "Maintain a comprehensive and continuously updated inventory of cryptographic assets.",
        ("ECHO", "OVERWATCH"),
        "Cryptographic inventory/CBOM records with provenance, freshness, ownership, and dependency links.",
    ),
    ControlMapping(
        "OMB-M26-15-AUTOMATION",
        "Use automation where feasible for discovery, policy enforcement, monitoring, and reporting.",
        ("ECHO", "PRIME", "OVERWATCH"),
        "Automated discovery inputs, policy results, dashboard metrics, exceptions, and operator review.",
    ),
    ControlMapping(
        "OMB-M26-15-AGILITY",
        "Design for cryptographic agility so algorithms and key-management capabilities can be changed with minimal disruption.",
        ("SARA", "PRIME", "ECHO"),
        "Configuration-controlled crypto choices, approved transition paths, compatibility evidence, and rollback records.",
    ),
    ControlMapping(
        "OMB-M26-15-SUPPLY",
        "Account for vendor, cloud, shared-service, and third-party dependencies in migration planning.",
        ("SARA", "ECHO", "OVERWATCH"),
        "Supplier/dependency register, readiness evidence, contract requirement status, and unresolved gaps.",
    ),
    ControlMapping(
        "OMB-M26-15-REPORT",
        "Track migration progress and provide leadership/compliance reporting from current evidence.",
        ("OVERWATCH", "ECHO", "SARA"),
        "Evidence-linked dashboards, milestones, exceptions, decision logs, and exportable status reports.",
    ),
)


def coverage_summary() -> dict[str, object]:
    modules = {module for item in MAPPINGS for module in item.modules}
    return {
        "mapping_count": len(MAPPINGS),
        "modules": tuple(sorted(modules)),
        "all_design_only": all(item.status == "DESIGN_MAPPING" for item in MAPPINGS),
        "claim_boundary": "REQUIREMENT_COVERAGE_MAPPING_NOT_FEDERAL_COMPLIANCE",
    }
