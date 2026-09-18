# BAROS Translational Risk Analysis Plan

Status: RESEARCH RISK-ANALYSIS ARTIFACT / NON-CLINICAL  
Clinical authority: NONE

## Purpose

This plan applies a risk-analysis structure compatible with the principles of
AAPM TG-100 to the BAROS translational workflow. It is not an institutional
FMEA and does not assign final clinical occurrence/severity/detectability
scores. Those values must be established by the partner clinical team for its
actual process, equipment, TPS, staffing, and intended use.

The purpose here is to expose failure pathways early, bind each pathway to
detectability/evidence, and define stop conditions before external validation.

## Proposed process map

1. research-case intake and identity check;
2. DICOM-RT object validation;
3. structure/nomenclature normalization;
4. frame/geometry/reference-chain validation;
5. model/parameter selection;
6. parameter identifiability and uncertainty assessment;
7. BAROS research optimization/evaluation;
8. hard-constraint and unsupported-case gate;
9. external TPS/research-dose-engine transfer;
10. independent dose recalculation;
11. dosimetric/DVH/gamma/robustness comparison;
12. qualified medical-physics review;
13. evidence-envelope construction;
14. contradiction/deviation adjudication;
15. exact-effect human authorization for next validation gate;
16. immutable evidence retention and claim dependency update.

## High-priority failure families

| Failure family | Example failure | BAROS prevention/detection control | External evidence required | Stop condition |
|---|---|---|---|---|
| Case identity / data association | wrong case, study, plan, or structure set associated | validation ID, UIDs, StudyInstanceUID/reference-chain checks, evidence hashes | partner data-custody/identity procedure | any unresolved identity mismatch |
| DICOM semantics | unsupported SOP/modality, missing required sequence, malformed RT object | fail-closed RTSTRUCT/RTPLAN/RTDOSE validator | target-TPS real-object interoperability set | unsupported/ambiguous semantics |
| Geometry | frame mismatch, orientation error, nonuniform or ambiguous RTDOSE spacing | FrameOfReferenceUID, origin/orientation/spacing/grid-offset validation | real TPS/dose-grid fixtures + independent physics review | any unresolved coordinate/geometry discrepancy |
| Dose scaling | wrong DoseGridScaling or relative/absolute interpretation | finite positive scaling checks, absolute-Gy requirement | independent TPS/dose-engine and measured-dose comparison | systematic or clinically material dose discrepancy |
| Structure semantics | incorrect ROI mapping/nomenclature | ROI reference checks; planned TG-263 normalization | partner structure dictionary and clinical adjudication | unresolved target/OAR identity |
| Biological-model selection | inappropriate TCP/NTCP/LQ formulation or parameters | explicit model identity, source/assumption traceability | domain-expert model review and locked parameter source | model not justified for intended-use population |
| Non-identifiability | multiple parameter combinations fit observations | SVD rank/nullity/condition assessment | intended-use sensitivity/data assessment | critical parameter state non-identifiable without mitigation |
| OOD / weak observability | optimizer acts on poorly observed biological state | observability-control hazard gate; unsupported-case refusal | partner-defined measurable state and OOD criteria | low-observability/high-control state without safety justification |
| Optimization | hard constraint bypass or unstable update | projected/backtracking optimizer + fail-closed hard constraints | external optimizer review/pathological cases | any hard-constraint bypass |
| Surrogate-to-physical gap | BAROS surrogate result treated as final dose | architecture requires external TPS/research-dose-engine recalculation | independent recalculated dose | no independent recalculation |
| TPS transfer | beam/control-point/structure semantics change on transfer | DICOM linkage and planned vendor-specific adapter tests | round-trip TPS evidence | any unresolved semantic loss |
| Deliverability | research plan cannot be delivered accurately | no internal claim; external deliverability gate | machine/phantom/QA measurement | failed deliverability criterion |
| Registration / accumulation | dose accumulated across mismatched anatomy/grids | aligned-grid-only accumulation; no implicit resampling | independently validated registration workflow | geometry mismatch without validated registration |
| QA interpretation | gamma aggregate hides localized material error | gamma is secondary; require absolute dose, DVH, localization | partner commissioning protocol | material local discrepancy despite aggregate gamma |
| Version drift | code/TPS/model/config changes after validation | commit/config/intended-use hashes, epoch/gate lock | change-control review | evidence does not match active version |
| Evidence corruption | analysis detached from raw data | raw/analysis hashes, environment/config provenance, dependency graph | partner-controlled evidence custody | hash/provenance failure |
| Contradictory evidence | independent result conflicts with BAROS result | contradiction quarantine | adjudication/repeat measurement | unresolved contradiction |
| Protocol deviation | post-hoc endpoint/configuration change | deviation field blocks promotion | institutional deviation review | unresolved material deviation |
| Authorization misuse | old approval reused after evidence/config change | exact-effect digest, nonce, expiry, expected epoch | institutional approval/signature integration | mismatch/replay/stale epoch |
| Claim persistence | invalidated calibration/model leaves downstream claim active | evidence dependency graph + blast-radius invalidation | reviewed evidence/claim graph | dependent claim not downgraded |
| Clinical authority creep | research software begins influencing treatment without authorization | patient_care_allowed hard false; G0-G9 gate model | IRB/regulatory/institutional authorization | any unapproved treatment influence |

## Failure-injection program

The partner-facing validation plan should deliberately inject or construct:

- mismatched UIDs and reference chains;
- wrong FrameOfReferenceUID;
- altered ImageOrientationPatient;
- nonuniform GridFrameOffsetVector;
- corrupted/incorrect DoseGridScaling;
- missing/renamed OAR/target structures;
- unsupported DICOM constructs;
- infeasible hard constraints;
- out-of-range biological parameters;
- rank-deficient parameter sensitivities;
- low-observability/high-control model states;
- stale model/configuration hashes;
- contradictory independent dose results;
- altered raw evidence after analysis;
- expired/replayed gate approvals;
- changed TPS/software versions after validation.

The correct result is frequently refusal/quarantine rather than successful plan
generation.

## Risk-management principle

BAROS should not be optimized solely for average plan quality. The translational
system is designed so that uncertainty, detectability, failure containment,
evidence provenance, and human authority remain separate hard constraints.

The partner institution will own the final clinical FMEA/process map and may
add, merge, re-score, or remove failure modes based on its actual workflow.
