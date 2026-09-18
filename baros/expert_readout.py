"""Expert-facing BAROS technical readout.

NON-CLINICAL. This module assembles bounded research evidence, governance state,
model-assurance capabilities, and external blockers into synchronized
machine-readable and human-readable reports. It does not convert internal
software verification into physical, clinical, or regulatory evidence.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .clinical_governance import GATES, REQUIRED_EVIDENCE
from .dvh import summarize_dose
from .pipeline import default_synthetic_case, run_synthetic_pipeline
from .robustness import evaluate_robustness, scale_influence


SCHEMA_VERSION = "baros.expert-readout.v2"


GATE_NAMES = {
    "G0": "requirements and traceability",
    "G1": "deterministic component verification",
    "G2": "end-to-end research pipeline",
    "G3": "numerical/model validation",
    "G4": "DICOM-RT interoperability/conformance",
    "G5": "external TPS/research-dose-engine integration",
    "G6": "physical/dosimetric verification",
    "G7": "held-out retrospective clinical validation",
    "G8": "independent replication and peer review",
    "G9": "prospective clinical/regulatory readiness",
}


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _model_registry() -> list[dict[str, Any]]:
    return [
        {
            "id": "BAROS-MODEL-LQ-001",
            "name": "linear-quadratic surviving fraction",
            "equation": "S(D)=exp(-(alpha*D + beta*D^2))",
            "role": "bounded radiobiological reference term",
            "parameters": ["dose_gy", "alpha_per_gy", "beta_per_gy2"],
            "clinical_parameterization": "NOT_ESTABLISHED",
            "assumption_boundary": "Numerical implementation only; no universal alpha/beta validity is claimed.",
        },
        {
            "id": "BAROS-MODEL-TCP-001",
            "name": "Poisson-form TCP reference",
            "equation": "TCP=exp(-sum(N_i*S_i))",
            "role": "bounded aggregation reference",
            "parameters": ["clonogen_counts", "surviving_fractions"],
            "clinical_parameterization": "NOT_ESTABLISHED",
            "assumption_boundary": "Reference calculation only; no indication-specific calibration is claimed.",
        },
        {
            "id": "BAROS-MODEL-NTCP-001",
            "name": "bounded sigmoid NTCP reference",
            "equation": "NTCP=1/(1+exp(-k*(D_eff-D50)))",
            "role": "bounded numerical response reference",
            "parameters": ["effective_dose_gy", "d50_gy", "slope_per_gy"],
            "clinical_parameterization": "NOT_ESTABLISHED",
            "assumption_boundary": "Not a claim that this is the clinically appropriate NTCP model for any site.",
        },
    ]


def _capability_matrix() -> list[dict[str, str]]:
    return [
        {
            "id": "BIO",
            "capability": "Radiobiological reference calculations",
            "implementation": "LQ survival, Poisson TCP, bounded sigmoid NTCP",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Independent model review and indication-specific parameter justification/calibration",
        },
        {
            "id": "OPT",
            "capability": "Constrained optimization",
            "implementation": "Deterministic projected/backtracking synthetic optimizer with hard max-dose rejection",
            "evidence": "SIMULATED_ONLY",
            "external_gate": "Independent optimization review, TPS/dose-engine coupling and deliverability validation",
        },
        {
            "id": "DICOM",
            "capability": "DICOM-RT semantic and geometry checks",
            "implementation": "RTSTRUCT/RTPLAN/RTDOSE validation, linkage, RTDOSE scaling and strict geometry extraction",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Real vendor/TPS conformance and interoperability testing",
        },
        {
            "id": "DVH",
            "capability": "Dose-volume analysis",
            "implementation": "Summary metrics, Vx, Dx%, empirical cumulative DVH",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Independent TPS/medical-physics reference comparison",
        },
        {
            "id": "GAMMA",
            "capability": "Gamma-index comparison",
            "implementation": "Pinned PyMedPhys wrapper with validation and failure checks",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Measurement-based QA under qualified medical-physics protocol",
        },
        {
            "id": "ROBUST",
            "capability": "Finite-scenario robustness",
            "implementation": "Explicit perturbation scenarios; any hard-constraint violation fails the gate",
            "evidence": "SIMULATED_ONLY",
            "external_gate": "Clinically justified uncertainty model and partner-controlled validation",
        },
        {
            "id": "ADAPT",
            "capability": "Cumulative aligned-dose handling",
            "implementation": "Summation only for identical frame/shape/origin/spacing/orientation",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Validated registration/resampling workflow before non-aligned accumulation",
        },
        {
            "id": "GOV",
            "capability": "Translational gate governance",
            "implementation": "Locked intended-use manifests, evidence envelopes, exact-effect authorization, monotonic epoch/replay protection",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Institutional role/signature integration and partner-controlled evidence custody",
        },
        {
            "id": "MODEL-AS",
            "capability": "Model and experiment-design assurance",
            "implementation": "Local identifiability SVD, expected-information-gain ranking, observability/controllability hazard checks",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Populate with clinically justified sensitivities, priors, costs, risks and measurable states",
        },
        {
            "id": "EVID-GRAPH",
            "capability": "Dependency-aware claim invalidation",
            "implementation": "Evidence/model/configuration/claim DAG, quarantine propagation and blast-radius analysis",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Bind real partner artifacts, calibrations, reviews and clinical claims into the graph",
        },
        {
            "id": "PROV",
            "capability": "Evidence provenance",
            "implementation": "Commit/configuration/input/runtime/dependency hashes and explicit claim state",
            "evidence": "BOUNDED_INTERNAL_VERIFICATION",
            "external_gate": "Partner custody, source-system provenance, reviewer identity and site evidence",
        },
    ]


def _gate_status(gate: str) -> str:
    if gate in {"G1", "G2"}:
        return "BOUNDED_INTERNAL_PASS"
    if gate in {"G0", "G3", "G4"}:
        return "PARTIAL_INTERNAL"
    return "OPEN_EXTERNAL"


def _readiness_gates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for gate in GATES:
        rows.append(
            {
                "gate": gate,
                "name": GATE_NAMES[gate],
                "status": _gate_status(gate),
                "required_evidence_kinds": sorted(REQUIRED_EVIDENCE[gate]),
                "external_evidence_present_in_this_readout": False,
            }
        )
    return rows


def _risk_families() -> list[dict[str, str]]:
    return [
        {"id": "RISK-IDENTITY", "family": "case identity / data association", "stop_condition": "unresolved patient/study/plan/structure identity mismatch"},
        {"id": "RISK-DICOM", "family": "DICOM semantics", "stop_condition": "unsupported or ambiguous semantics"},
        {"id": "RISK-GEOM", "family": "coordinate / dose-grid geometry", "stop_condition": "unresolved frame/orientation/spacing discrepancy"},
        {"id": "RISK-DOSE-SCALE", "family": "dose scaling / units", "stop_condition": "systematic or clinically material dose discrepancy"},
        {"id": "RISK-STRUCT", "family": "structure identity / nomenclature", "stop_condition": "unresolved target/OAR identity"},
        {"id": "RISK-MODEL", "family": "biological model selection / parameter validity", "stop_condition": "model or parameter set not justified for locked intended use"},
        {"id": "RISK-ID", "family": "parameter non-identifiability", "stop_condition": "critical parameter state non-identifiable without mitigation"},
        {"id": "RISK-OOD", "family": "low observability / high control", "stop_condition": "high-actuation state lacks adequate observability or refusal rule"},
        {"id": "RISK-OPT", "family": "optimization / hard-constraint bypass", "stop_condition": "any hard-constraint bypass"},
        {"id": "RISK-SURR", "family": "surrogate-to-physical dose gap", "stop_condition": "no independent TPS/research-dose-engine recalculation"},
        {"id": "RISK-XFER", "family": "TPS transfer / semantic loss", "stop_condition": "unresolved transfer or round-trip semantic loss"},
        {"id": "RISK-DELIV", "family": "machine deliverability", "stop_condition": "failed deliverability criterion"},
        {"id": "RISK-REG", "family": "registration / dose accumulation", "stop_condition": "geometry mismatch without validated registration"},
        {"id": "RISK-QA", "family": "QA aggregate hides local failure", "stop_condition": "clinically material localized discrepancy"},
        {"id": "RISK-VERSION", "family": "version / configuration drift", "stop_condition": "evidence does not match active software/TPS/model/configuration"},
        {"id": "RISK-EVID", "family": "evidence corruption / provenance break", "stop_condition": "hash or custody failure"},
        {"id": "RISK-CONTRA", "family": "contradictory evidence", "stop_condition": "unresolved contradiction"},
        {"id": "RISK-DEVIATION", "family": "protocol deviation", "stop_condition": "unresolved material deviation"},
        {"id": "RISK-AUTH", "family": "authorization replay / stale approval", "stop_condition": "approval does not bind exact current effect"},
        {"id": "RISK-CLAIM", "family": "stale claim after evidence/model change", "stop_condition": "dependent claim not downgraded"},
        {"id": "RISK-AUTHORITY", "family": "clinical authority creep", "stop_condition": "any unapproved treatment influence"},
    ]


def build_expert_readout(*, commit_sha: str = "UNPINNED") -> dict[str, Any]:
    """Build a deterministic expert-oriented readout for the bounded reference case."""
    case = default_synthetic_case()
    evidence = run_synthetic_pipeline(case, commit_sha=commit_sha)
    dose = [float(value) for value in evidence["result"]["dose_gy"]]

    tumor_dose = [dose[index] for index in case.tumor_voxels]
    oar_indices = sorted(case.oar_max_gy)
    oar_dose = [dose[index] for index in oar_indices]

    target_summary = asdict(summarize_dose(tumor_dose))
    oar_summary = asdict(summarize_dose(oar_dose))

    scenarios = {
        "dose_minus_5pct": scale_influence(case.influence, 0.95),
        "nominal": case.influence,
        "dose_plus_5pct": scale_influence(case.influence, 1.05),
    }
    robustness = evaluate_robustness(
        weights=evidence["result"]["weights"],
        influence_scenarios=scenarios,
        tumor_voxels=case.tumor_voxels,
        alpha_per_gy=case.alpha_per_gy,
        beta_per_gy2=case.beta_per_gy2,
        hard_max_gy=case.oar_max_gy,
    )

    constraint_readout = []
    for index in oar_indices:
        limit = float(case.oar_max_gy[index])
        observed = float(dose[index])
        constraint_readout.append(
            {
                "voxel_index": index,
                "limit_gy": limit,
                "observed_gy": observed,
                "margin_gy": limit - observed,
                "satisfied": observed <= limit,
            }
        )

    baseline_objective = float(evidence["baseline"]["tumor_survival_objective"])
    final_objective = float(evidence["result"]["tumor_survival_objective"])
    objective_reduction = baseline_objective - final_objective
    fractional_reduction = 0.0 if baseline_objective == 0.0 else objective_reduction / baseline_objective

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "system": {
            "name": "BAROS",
            "expanded_name": "Biologically Adaptive Radiotherapy Optimization System",
            "mode": "NON_CLINICAL_RESEARCH",
            "patient_care_allowed": False,
            "partner_validation_ready": True,
            "patient_care_ready": False,
            "commit_sha": commit_sha,
        },
        "research_question": (
            "Can explicitly identified radiobiological objective terms be combined with hard dosimetric "
            "constraints, fail-closed DICOM/data handling, model-assurance checks, evidence-state governance, "
            "robustness evaluation and auditable provenance without bypassing independently commissioned TPS "
            "dose calculation, measurement QA or human clinical authority?"
        ),
        "models": _model_registry(),
        "optimization": {
            "algorithm_class": "deterministic projected/backtracking gradient optimization on synthetic influence matrix",
            "objective": "mean LQ surviving fraction over designated tumor voxels",
            "baseline_objective": baseline_objective,
            "final_objective": final_objective,
            "absolute_objective_reduction": objective_reduction,
            "fractional_objective_reduction": fractional_reduction,
            "iterations": int(evidence["result"]["iterations"]),
            "converged": bool(evidence["result"]["converged"]),
            "hard_constraints_satisfied": bool(evidence["pass_conditions"]["hard_constraints_satisfied"]),
            "clinical_deliverability_claimed": False,
        },
        "dose_readout": {
            "dose_gy": dose,
            "target_indices": list(case.tumor_voxels),
            "target_summary": target_summary,
            "oar_indices": oar_indices,
            "oar_summary": oar_summary,
            "hard_constraint_margins": constraint_readout,
            "physical_dose_accuracy_claimed": False,
        },
        "synthetic_biology_readout": {
            "tcp": float(evidence["result"]["synthetic_tcp"]),
            "ntcp": float(evidence["result"]["synthetic_ntcp"]),
            "clinical_interpretation_permitted": False,
        },
        "robustness": {
            "scenario_names": [item.name for item in robustness.scenarios],
            "worst_objective_scenario": robustness.worst_objective_scenario,
            "worst_tumor_survival_objective": float(robustness.worst_tumor_survival_objective),
            "all_hard_constraints_satisfied": bool(robustness.all_hard_constraints_satisfied),
            "scenarios": [
                {
                    "name": item.name,
                    "dose_gy": list(item.dose_gy),
                    "tumor_survival_objective": float(item.tumor_survival_objective),
                    "hard_constraints_satisfied": bool(item.hard_constraints_satisfied),
                    "constraint_failures": list(item.constraint_failures),
                }
                for item in robustness.scenarios
            ],
            "clinical_uncertainty_model_claimed": False,
        },
        "governance": {
            "intended_use_manifest_implemented": True,
            "evidence_envelope_implemented": True,
            "contradiction_and_deviation_quarantine_implemented": True,
            "exact_effect_gate_authorization_implemented": True,
            "durable_epoch_and_replay_guard_implemented": True,
            "current_partner_validation_manifest_locked": False,
            "external_evidence_envelope_present": False,
        },
        "model_assurance": {
            "local_identifiability_analysis_implemented": True,
            "information_gain_experiment_ranking_implemented": True,
            "observability_controllability_hazard_detection_implemented": True,
            "clinical_sensitivity_matrix_supplied": False,
            "clinical_prior_covariance_supplied": False,
            "clinical_model_identifiability_established": False,
        },
        "evidence_dependency_control": {
            "dependency_graph_implemented": True,
            "transitive_claim_eligibility_implemented": True,
            "quarantine_propagation_implemented": True,
            "blast_radius_invalidation_implemented": True,
            "external_partner_graph_populated": False,
        },
        "capabilities": _capability_matrix(),
        "readiness_gates": _readiness_gates(),
        "risk_families": _risk_families(),
        "safety_invariants": [
            "No patient-care or treatment authority from repository evidence.",
            "Hard configured dose constraints fail closed in the bounded optimizer.",
            "Unsupported or malformed bounded DICOM-RT inputs fail validation.",
            "Ambiguous or non-aligned dose-grid geometry is not silently registered or resampled.",
            "BAROS surrogate/numerical dose is never represented as independently commissioned final clinical dose.",
            "Synthetic TCP/NTCP and reliability values cannot be promoted into clinical outcome claims.",
            "External gate promotion requires partner-controlled evidence and independent review.",
            "Contradictions and material protocol deviations block evidence promotion.",
            "Authorization is bound to exact intended use, commit, evidence, gate transition, environment and epoch.",
            "Changed or quarantined evidence must invalidate dependent claims rather than leave stale promotion active.",
        ],
        "partner_execution_package": [
            "Freeze one intended-use manifest: indication, stage/risk group, technique, machine class, TPS/version, fractionation, comparator, endpoints, operator roles and overrides.",
            "Populate model-assurance inputs: parameter sources, sensitivity matrices, priors/uncertainty, identifiability limits and out-of-distribution/refusal criteria.",
            "Execute independent numerical/model verification and parameter/uncertainty review.",
            "Exercise real RTSTRUCT/RTPLAN/RTDOSE objects and vendor/TPS edge cases under governed conditions.",
            "Recalculate any BAROS research proposal using the partner TPS or approved independent dose engine.",
            "Perform commissioning-style absolute-dose, spatial, DVH/structure, deliverability, phantom and end-to-end measurements.",
            "Wrap raw and analysis artifacts in partner-controlled evidence envelopes with custody, uncertainty, deviations, contradictions and reviewer identity.",
            "Populate the evidence dependency graph so changed calibrations/models/configurations automatically expose affected claims.",
            "Run held-out retrospective comparison with predeclared metrics and independent adjudication.",
            "Proceed to prospective shadow mode only after preceding gates pass and institutional review permits it.",
        ],
        "external_blockers": [
            "No partner-locked intended-use manifest.",
            "No qualified partner TPS/vendor interoperability evidence.",
            "No independent measured-dose or phantom evidence.",
            "No indication-specific clinically justified biological parameter set.",
            "No clinical sensitivity/prior dataset establishing model identifiability.",
            "No validated deformable registration/dose accumulation for non-aligned grids.",
            "No partner-populated external evidence dependency graph.",
            "No held-out retrospective clinical validation.",
            "No prospective shadow-mode or interventional clinical evidence.",
            "No settled FDA classification, submission pathway or authorization.",
        ],
        "source_evidence": {
            "synthetic_pipeline_evidence_sha256": str(evidence["evidence_sha256"]),
            "case_sha256": str(evidence["case_sha256"]),
            "runtime_provenance": evidence["runtime_provenance"],
            "claim_state": str(evidence["claim_state"]),
            "passed": bool(evidence["passed"]),
        },
    }
    report["readout_sha256"] = _canonical_hash(report)
    return report


def render_expert_markdown(report: dict[str, Any]) -> str:
    """Render an expert-facing Markdown summary from a readout."""
    system = report["system"]
    optimization = report["optimization"]
    dose = report["dose_readout"]
    robustness = report["robustness"]

    lines = [
        "# BAROS Expert Technical Readout",
        "",
        f"Schema: {report['schema_version']}",
        f"Commit: {system['commit_sha']}",
        f"Mode: {system['mode']}",
        f"Patient-care allowed: {system['patient_care_allowed']}",
        f"Partner-validation ready: {system['partner_validation_ready']}",
        f"Patient-care ready: {system['patient_care_ready']}",
        f"Readout SHA-256: {report['readout_sha256']}",
        "",
        "## Research question",
        "",
        report["research_question"],
        "",
        "## Quantitative bounded-reference readout",
        "",
        f"- Objective: {optimization['objective']}",
        f"- Baseline objective: {optimization['baseline_objective']:.12g}",
        f"- Final objective: {optimization['final_objective']:.12g}",
        f"- Fractional objective reduction: {optimization['fractional_objective_reduction']:.6%}",
        f"- Iterations: {optimization['iterations']}",
        f"- Converged: {optimization['converged']}",
        f"- Hard constraints satisfied: {optimization['hard_constraints_satisfied']}",
        f"- Target mean dose (synthetic Gy): {dose['target_summary']['dmean_gy']:.12g}",
        f"- OAR mean dose (synthetic Gy): {dose['oar_summary']['dmean_gy']:.12g}",
        f"- Worst robustness scenario: {robustness['worst_objective_scenario']}",
        f"- Robust hard-constraint gate: {robustness['all_hard_constraints_satisfied']}",
        "",
        "### Hard-constraint margins",
        "",
        "| Voxel | Limit Gy | Observed Gy | Margin Gy | Pass |",
        "|---:|---:|---:|---:|:---:|",
    ]
    for item in dose["hard_constraint_margins"]:
        lines.append(
            f"| {item['voxel_index']} | {item['limit_gy']:.6g} | {item['observed_gy']:.6g} | "
            f"{item['margin_gy']:.6g} | {item['satisfied']} |"
        )

    lines += [
        "",
        "## Capability/evidence matrix",
        "",
        "| ID | Capability | Implementation | Evidence | Next external gate |",
        "|---|---|---|---|---|",
    ]
    for item in report["capabilities"]:
        lines.append(
            f"| {item['id']} | {item['capability']} | {item['implementation']} | "
            f"{item['evidence']} | {item['external_gate']} |"
        )

    lines += [
        "",
        "## Validation readiness gates",
        "",
        "| Gate | Domain | Status | Required evidence kinds |",
        "|---|---|---|---|",
    ]
    for item in report["readiness_gates"]:
        required = ", ".join(item["required_evidence_kinds"])
        lines.append(f"| {item['gate']} | {item['name']} | {item['status']} | {required} |")

    lines += [
        "",
        "## Translational governance state",
        "",
    ]
    for key, value in report["governance"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Model-assurance state",
        "",
    ]
    for key, value in report["model_assurance"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Evidence-dependency control state",
        "",
    ]
    for key, value in report["evidence_dependency_control"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Risk families / stop conditions",
        "",
        "| ID | Failure family | Stop condition |",
        "|---|---|---|",
    ]
    for item in report["risk_families"]:
        lines.append(f"| {item['id']} | {item['family']} | {item['stop_condition']} |")

    lines += ["", "## Safety invariants", ""]
    lines.extend(f"- {item}" for item in report["safety_invariants"])
    lines += ["", "## Partner execution package", ""]
    lines.extend(f"{index}. {item}" for index, item in enumerate(report["partner_execution_package"], 1))
    lines += ["", "## External blockers", ""]
    lines.extend(f"- {item}" for item in report["external_blockers"])
    lines += [
        "",
        "## Claim boundary",
        "",
        "This readout is research-software evidence. It does not establish commissioned physical dose accuracy, "
        "clinically valid biological parameters, clinical safety/effectiveness, treatment success, regulatory "
        "authorization, or patient-care readiness.",
        "",
    ]
    return "\n".join(lines)
