# BAROS EvidenceGate — independent evaluation preregistration template (draft, NON-CLINICAL)

**Prepared:** 2026-11-17. **Not preregistered, approved or accepted by an external investigator.** This is an offer of an evaluator-controlled study framework. No data sharing, IRB determination or irradiation is authorized by this text.

## Core scientific question

Does a pre-TPS, evidence-and-model-qualified biological-input decision gate identify disqualifying research adaptation proposals missed by fair, prespecified comparators **without intolerable unnecessary abstention, workflow overhead or hidden failures**?

The independent medical-physics team—not WorldShepherd—must select and freeze (a) indication and technique, (b) biological input and measurement protocol, (c) TPS/version/commissioned dose environment, (d) allowed plan/structure/dose data and data rights, (e) challenge cases and blinded reference labels, (f) comparator implementation, (g) clinical relevance and (h) physical dosimetry tolerances. All adverse and null results remain publishable subject to lawful agreements. Developer cannot adjudicate clinical ground truth.

## Stage A — research software and interoperability (NO patient care)

- **Unit of analysis:** frozen research proposal decision, not a patient treatment.
- **Lock before revealing labels:** code/commit hashes, exact requirements and use restrictions, schema/thresholds, synthetic generator seed, reference UID checks, model, environment, evidence lineage, comparators and analysis plan.
- **Challenge families:** DICOM RT UID/frame mismatch, invalid dose scaling/units, nonuniform grid spacing, out-of-order timepoints, missing/contradictory measurement, misregistration, low quality, locally unidentifiable sensitivity, OOD input, misassociated case, revoked source evidence, forced override after qualification failure and a preserved +5% dose perturbation hard-constraint failure.
- **Critical failure:** any disqualified input still permits a proposal; patient-treatment authority appears; last-valid-plan identity is not preserved; corrupt evidence is accepted silently; essential mismatch or numerical breach is hidden. ANY critical failure means STOP for clinical progression.
- **Comparators:** full BAROS gate; genuinely literature-reproduced quality/uncertainty/OOD method (not yet built); trigger-only negative control; always-abstain baseline; partner-selected actual planning process. The current limited synthetic quality-only heuristic is NOT a faithful reproduction of any commercial or published method.
- **Primary metrics and denominators:** critical false-proceed, eligible proposal recall, unjustified abstention, no-trigger false proposal, failure reason accuracy, record replay equality, decision latency, workflow burden and physician/physicist interpretability. Report exact counts, statistical uncertainty, all negative results and audit hashes. Five synthetic cases cannot establish clinical reliability.
- **No prohibited clinical actions:** no dose escalation, prescription/fractionation change, hardware commands, interpretation as a physician order, or patient plan approval.

## Stage A2 — paired, locked uncertainty/comparator challenge (developer interface built; NOT independently run)

A paired scorer is now available in `baros/paired_comparator.py` with unit tests. Its purpose is **case-matched comparison under a single frozen research challenge**, NOT a clinical head-to-head study. This design closes a source of avoidable benchmark bias: separate cohorts, mismatched IDs or post-hoc thresholds can create misleading performance improvements.

**Pre-unblinding requirements controlled by the evaluator:**

1. Freeze the same `protocol_id` and SHA-256 *challenge manifest* for the full BAROS proposal submission and independent `LockedScoreSubmission`. The comparator's `challenge_sha256` is mandatory for paired claims; standalone exploratory comparator reports may omit it.
2. Independently determine the *triggered* research case cohort **before** either system sees hidden labels. Its two reference strata are qualified-trigger and disqualified-trigger. **No-trigger cases form a separate, independently preregistered stratum** using the three-class blinded scorer; never discard them after scores are inspected.
3. Secure institutional protocol approvals, intended-use and data rights. Lock the exact experimental stimulus, biomarker interpretation, uncertainty method, dose/TPS boundaries, reference labels in separate custody and a scientific baseline algorithm. The comparator's quantitative risk score must come from the **actual documented method**, not a developer-selected toy score.
4. Freeze a prespecified operating threshold **or complete sorted grid** before label release, and report **all grid points**, including null findings. Do not optimize on the held-out set and then advertise the best point without separate validation.
5. Lock the exact BAROS commit/build, external method version/calibration population, dependencies, environment, challenge digest, each submission digest and independent holdout label manifest before unblinding. Software SHA-256 is *integrity metadata*, **not authenticated or independently witnessed custody**.
6. After release, score with `compare_frozen_research_submissions(...)`. Demand exact common protocol, challenge digest and case-ID set; reject mismatches, invalid samples, tampered records and any treatment authority. Report disqualified-proposal rates, eligible proposal recall, total coverage and **paired discordant cases**, with numerator/denominator and appropriate uncertainty. The paired discordance counts are descriptive; there is **no significance test, causal proof, device-certification inference or probability-of-patient-harm estimate**.
7. If the external method is an uncertainty/OOD segmenter from the 2026 MR-guided ART literature, acknowledge that its *prostate MRI segmentation outputs are not calibrated FMISO-PET hypoxia measurements*. The physicist must determine whether that is a defensible scientific comparator for the chosen target before running any clinical study. Otherwise report it as an exploratory software-method comparison and seek a better matched baseline.

**Acceptance remains OPEN:** no independent method scores, evaluator-owned cases/labels, or authorized clinical measurements have yet been supplied. The current test fixtures in this repository are developer-authored synthetics and are **not** an independent challenge. One observed difference in these fixtures does not demonstrate competitive superiority, let alone patient benefit.

## Stage B — conditional independent TPS and physical feasibility

Proceed only with an institution-approved workshare, legally accessible data, responsible clinical team and successful Stage A.

- Medical physicist freezes accepted modalities, machine/technique, TPS build and reference plan, the independent recalculation procedure, allowable geometry units, DICOM RT semantics, hard target/OAR conditions, phantom test geometry, measurement/calibration procedure and all pass/fail tolerances BEFORE execution.
- Compare verified, partner-produced TPS-calculated and where applicable physically measured plans, recording DVH/constraint violations, out-of-setup errors, registration and dose scale/geometry mismatches, throughput and false abstentions. Do not invent dosimetric tolerances in the developer's tests.
- If a research biological intent is ever translated into an optimization input, freeze the objective transformation and preserve full TPS and human authority. Plan transfer or physical dose accuracy are not established by synthetic success.

## Stage C — conditional held-out retrospective investigation

Only with appropriate approvals: partner-controlled deidentified cases, biomarker calibration and temporally paired measurements, independent labels, preregistered analysis, missingness/uncertainty characterization, and explicit comparison against normal clinical workflows. Prospective shadow-mode or interventional studies require further separate authorizations.

## Hard stopping rules

1. Unlicensed data use, privacy/PHI exposure, or broken source/decision provenance.
2. Any silent proposal from disqualified biological evidence or any clinical treatment-authority claim.
3. Any unadjudicated physical/geometry or hard clinical constraint discrepancy, or serious patient-safety concern.
4. Biomarker/indication not realistically observable, legal data path unavailable, TPS inaccessible, or differentiation fails under fair comparator.
5. Clinical staff or institutional requirements cannot be met lawfully and independently.

## Deliverables owned by an external evaluator

- Dated accepted study protocol with frozen independent cases, reference labels, roles, prior-art comparators, IRB/ethics determination.
- Secure licensed data manifest under institutional custody; no patient images or identifiers committed into GitHub.
- Independent physics measurements and TPS acceptance record, including negative results and exact frozen tolerances.
- Reproducibility/uncertainty report, with case denominators, result hashes, model versions and independent failure adjudication.
- Explicit PASS/FAIL/PARTIAL/STOP conclusion; no sponsor preference for a favorable result.

## External readiness

As of this draft, no independent medical physicist/physician has agreed to evaluate the product; no signed data license, commissioned TPS access, institution-owned preregistration, physical measured dose, clinical dataset or sponsored workshare is in place. This document does NOT satisfy those external criteria by itself.

The founder retains pre-existing IP; any data access, evaluation, licensing, payment, publications, ethics/IRB governance and conflict-of-interest structure requires separate institutional and legal agreements. This scope does not itself authorize expenditure, company filing, patient contact, or disclosure of confidential information.

**Related materials:** short BAROS methods manuscript dated 2026-11-17; doctoral-review acceptance register; current BAROS decision audit, DICOM RT validator, model assurance and phase-1 comparator tests.
