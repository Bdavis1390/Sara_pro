# BAROS EvidenceGate: A Research-Stage, Fail-Closed Biological-Evidence Qualification Boundary for Adaptive Radiotherapy

**Short methods manuscript — DRAFT v0.4, 2026-11-17.**
**Author:** Brandon Ray Davis, WorldShepherd R&D, USA. Technical drafting and editorial assistance from an AI system; the human author is responsible for source verification and all scientific claims.
**Category:** preclinical software-methods / translational engineering. **Not a clinical evaluation, peer-reviewed article, FDA submission, or independent dosimetric validation.**
**Prior work:** a 761-page May 2026 BAROS technical monograph exists separately; it is not incorporated wholesale and does not independently establish any result reported here.

## Abstract (≈200 words)

Biologically adaptive radiotherapy is limited by uncertainty in interpreting longitudinal images and biomarkers and by the need to preserve an independently governed treatment-planning and delivery workflow. We describe **BAROS EvidenceGate**, an early-stage, **pre-treatment-planning-system (pre-TPS)** software qualification boundary that evaluates whether an observed biological-state change can justify a **research reoptimization proposal** or requires abstention/fallback. The decision contract explicitly checks measurement quality, state uncertainty, geometry qualification, local model-identifiability status and out-of-distribution flags; proposal permission never constitutes treatment authorization. In the current implementation, biological state/decision logic and evidence-governance machinery exist as separate software components; full production integration with a commissioned TPS, biological signal calibration, and dose delivery is **not implemented or validated**. To make basic behavior falsifiable, we created deterministic synthetic negative-control combinations and a 12-fixture benchmark comparing the full gate with trigger-only, restricted data-quality/OOD-only and always-abstain rules. At frozen development commit `736799122c626b8a0dc32ab27d3ba9ab662aa7d0`, CI recorded **280 passing bounded research-software tests and two warnings**, including research-only synthetic objective-priority and FMISO metadata/reader checks. In the 12 controlled fixtures, the full gate permitted proposals in 5/5 prespecified qualified-trigger cases and 0/5 disqualified-trigger cases. This is developer-authored policy conformance, **not clinical reliability, safety, or superiority**. We identify the additional independent biomarker, TPS/dosimetry and clinical-evaluation evidence needed before translational conclusions.

**Keywords:** adaptive radiotherapy; biological uncertainty; abstention; treatment-planning systems; provenance; preclinical software verification.

## 1. Introduction

Adaptive radiotherapy already encompasses anatomy-based replanning, commercial treatment-planning systems (TPS), dose optimization, quality assurance and clinical authorization. Biologically individualized planning has additionally examined tumor hypoxia and other biomarkers, but spatial/temporal variation, imaging calibration, uncertainty and nonrepeatability make a biomarker-driven plan change difficult to justify. Studies of FMISO-PET in head-and-neck cancer illustrate both biological motivation and unresolved repeatability, access and evidence limitations [1,2]. Existing research also studies uncertainty and out-of-distribution detection in adaptive radiotherapy, while commercial systems use robust optimization, supervised adaptive workflows, quality checks and end-to-end QA [3–6]. **None of those ideas is claimed here as newly invented.**

The narrow engineering problem is **decision provenance and pre-proposal qualification**: a biological measurement may be different without providing sufficiently reliable evidence to alter a plan. A safe research software interface should record the disqualifying reason, reject manual bypass of qualification, preserve the prior plan identity, and avoid granting treatment authority. The scientific and commercial question is whether the *combined contract* provides incremental value relative to existing approaches, an issue **not settled by this work**.

**Research contribution claimed:** an executable, bounded **decision-eligibility contract** for longitudinal biological research inputs and its negative-control verification strategy. We make no claim to a novel radiobiological law, new clinical plan optimizer, measurement of tumor hypoxia, commercial TPS integration, dose painting efficacy, regulatory clearance or clinical superiority.

## 2. Methods

### 2.1 Intended use and system boundary

The current bounded workflow is: **input observation -> state validation -> trigger assessment -> qualification/abstention -> permitted *research proposal* -> independent TPS/dosimetry (future) -> authorized clinical judgment (external)**.

The primary decision outputs are a **status and preserved plan identity**, not a DICOM-RT prescription or an approved deliverable plan. A separate, optional **synthetic-only objective-intent module** illustrates bounded dimensionless region-priority deltas, but cannot export those values to any commissioned TPS or prescribe dose. On a qualified trigger, the software may propose research reoptimization while retaining the last valid governed plan identity; the commissioned TPS and credentialed clinical team would remain authoritative. The software does not generate a clinical plan or authorize treatment. The labels 'hold' and 'fallback' describe *software state*, not an instruction to operate a linac.

The research state `BiologicalState` carries phase index, per-voxel estimated `alpha_per_gy` and `beta_per_gy2`, hypoxia and resistance indices, per-voxel uncertainty, anatomical/motion change, measurement quality, geometry qualification, identifiability status and OOD status [7]. **These arrays are synthetic in the current verification**, not biologically calibrated voxel-level truths. Parameter units/normalization need to be established with an investigator for any real study.

### 2.2 Trigger, qualification and abstention logic

For previous state `x(t-1)`, current `x(t)` and locked threshold tuple `tau`, a trigger occurs when a validated delta in hypoxia index, resistance index, uncertainty, anatomy or motion crosses the corresponding threshold. These thresholds are configurable, not clinically validated. The input validation enforces finite, aligned nonnegative arrays, a bounded quality score, strictly typed Boolean qualification flags, and strictly increasing integer phase indices. A measured zero difference must not trigger merely because a configured threshold equals zero.

The qualification predicate is

`Q(x) = geometry_ok AND model_identifiable AND NOT OOD AND (measurement_quality >= qmin) AND (max_uncertainty <= umax)`.

The **proposal** predicate is `P = trigger AND Q(x[t-1]) AND Q(x[t])`. Both the prior and current measurements must be qualified: a high-quality new image cannot retroactively validate an untrustworthy comparison baseline. If a trigger occurs and either state is disqualified, the result holds the research last-valid plan identity or falls back to a declared standard identity. If no trigger is present, no new proposal is issued. A `manual_force` flag may request trigger evaluation but **cannot override** quality blockers. The `treatment_authority` field is always false. See `baros/closed_loop.py` and `tests/test_baros_phase1_qualification_matrix.py` [7].

### 2.2.1 Experimental, nonclinical objective-intent mapping

For the reviewer-requested implementation boundary, `baros/research_objective_intent.py` has a deliberately toy mapping from the positive difference in a **dimensionless synthetic hypoxia index** to a bounded **dimensionless abstract priority increment** for each synthetic region:

`delta_priority[i] = min(cap, gain * max(0, hypoxia[i,t] - hypoxia[i,t-1]))`.

The `gain` and `cap` inputs are arbitrary research constants in [0,1], **not clinician-calibrated planning weights**. Both longitudinal states must pass the decision qualification; an eligible hypoxia-change trigger is required before any priority values can be emitted. The result is marked `dose_or_prescription_defined=False`, `tps_export_allowed=False`, `treatment_authority=False`. Synthetic region identifiers are not actual clinical target/OAR labels. A named TPS adapter, clinically meaningful objective interpretation, dosimetric transfer and deliverability review are **not implemented**. This is a falsifiable software API example, not evidence of a biological treatment-planning innovation.

This system is a *policy contract*. Clinical experts must still decide whether these exact variables or thresholds are appropriate for any proposed biological signal.

### 2.2.2 Declared FMISO provenance and reader-interpretation check (synthetic only)

A separate *mock* input screen at `baros/fmiso_interpretation_gate.py` rejects a serial FMISO research pair if declared acquisition/quantification protocols or common-reference digests differ, images appear identical, registration review is absent, or two separately declared readers disagree, are indeterminate or lack declared protocol training. This conservative mock design is motivated by published interreader variability and benefits of trained interpretation [10]. It also rejects FDG as an FMISO substitute. **The reader identities, image hashes and training/registration attestations are supplied by developer test fixtures, not independently authenticated.** A passing metadata screen **does not** establish biological signal accuracy, clinical reader competence, test–retest repeatability, a numerical hypoxia cutoff or appropriate radiotherapy dose adaptation.

Importantly, a baseline and *on-treatment* PET change may contain both real therapy response and measurement/registration noise. It is **not** the same as a short-interval scan-repeatability study without intervening therapy [1]. Those scientific distinctions must be resolved by the qualified external assay team before any clinical interpretation or TPS experiment.

### 2.3 Evidence and governance

A separate `baros/clinical_governance.py` module defines intended-use/evidence envelopes, gate requirements, provenance hashes, external-partner evidence categories and human authorization requirements for research governance [7]. A SHA-256-bound decision audit and blinded-label fixture runner provide research replay and an evaluator handoff format; neither authenticates an institution, verifies a source measurement or constitutes independent clinical testing. It prevents a research envelope from authorizing patient care. Integration of all governance prerequisites into a single immutable event payload spanning a real TPS remains future engineering and is **not demonstrated** by the negative-control unit tests.

### 2.4 Frozen synthetic challenge cases and controls

We designed two **developer-authored** test layers, neither representing a patient sample:

1. Exhaustive combinations of five binary disqualification dimensions—geometry, identifiability, OOD, measurement quality and uncertainty—test that a triggered input can issue a research proposal only when all five conditions are met. Thirty-two combinations are tested, along with forced-trigger bypass, reversed/invalid phase and non-finite uncertainty.
2. A 12-case descriptive test set contains five **qualified-trigger**, five **disqualified-trigger** (one per quality-blocker class) and two **no-trigger** fixtures. The same inputs are compared under four nonclinical policies: (A) full EvidenceGate; (B) trigger-only, intentionally unsafe; (C) *restricted synthetic quality/OOD-only* gate that omits geometry and identifiability; (D) always abstain. **C is not a faithful reproduction of a published method or a vendor product**. Cases and expected labels are authored by the same development team and do not establish independent classification validity.

Endpoints are (i) false-proceed among prespecified disqualified-trigger cases; (ii) eligible proposal recall; and (iii) spurious proposal among no-trigger cases. Numerators and denominators, plus descriptive Wilson score intervals, are reported by the software. A zero count in five cases must never be read as a demonstrated population safety rate. No inferential superiority test is performed.

### 2.5 Future validation stages

**Stage 0A:** permitted, de-identified **DICOM-RT structural/reference** checks with legally accessible plan/structure/dose samples, using versioned schemas and synthetic corruptions. This only tests data interoperability, not actual TPS dose recalculation.

**Stage 0B:** independent investigators preregister challenge cases, labels and realistic comparators; measure error/abstention coverage and workflow burden without patient care.

**Stage 1:** after institutional approval, a qualified medical physicist independently evaluates one biomarker/indication/TPS/version combination, commissioned plan recalculation, geometry, dose, hard clinical constraints and relevant phantom/end-to-end measurements using *externally set tolerances*. This must precede clinical utility claims.

**Stage 2:** a properly governed, held-out retrospective study, with independent clinical interpretation and applicable data/privacy/ethics approvals. Prospective shadow mode, interventional evaluation and clinical use require **separate later authorization**.

## 3. Results — internally controlled software only

CI on exact commit `736799122c626b8a0dc32ab27d3ba9ab662aa7d0` completed **280 passing bounded research tests with two warnings**, plus successful required build/freshness workflows. Checks include two-timepoint qualification, 1,024 synthetic prior/current quality permutations, strict input types, a label-separated challenge interface, matched synthetic comparators, Shannon entropy/mutual-information reference formulas, synthetic-only objective priority changes and a mock FMISO reader/protocol consistency gate. None of these has been independently operated with a clinical data source or commissioned TPS. This includes functionality not limited to the 12 comparator fixtures. The test set has small, deterministic, developer-authored strata and does not approximate patient heterogeneity.

| Nonclinical policy (12 fixtures) | Disqualified-trigger proposals / 5 | Qualified-trigger proposals / 5 | No-trigger proposals / 2 |
|---|---:|---:|---:|
| Full EvidenceGate | 0/5 | 5/5 | 0/2 |
| Restricted quality/OOD-only heuristic | 2/5 | 5/5 | 0/2 |
| Trigger-only | 5/5 | 5/5 | 0/2 |
| Always abstain | 0/5 | 0/5 | 0/2 |

These values are *constructed behavioral demonstrations*. For example, the restricted heuristic's two false proceeds were induced by deliberately excluding geometry and identifiability requirements; they **cannot establish a measured advantage over deployed commercial or published adaptive techniques**. The always-abstain comparison demonstrates why false-proceed alone is an inadequate optimization target.

An earlier +5% synthetic dose perturbation violated a declared hard constraint; this failure remains disclosed and is **not superseded** by later software pass counts. No measured phantom dose, gamma pass rate, TPS-deliverability pass, retrospective patient endpoint or independent study result is available.

## 4. Discussion

The result is useful as **software-contract verification**: controls can refuse unqualified research proposals while preserving a valid plan identity, even when a trigger or manual force exists. The essential unsolved question is whether clinicians need this external qualification layer, whether the selected biological inputs are identifiable and repeatable enough, and whether existing TPS/vendor/local QA methods already address the same failure category more effectively.

The proposed initial **HNSCC / serial 18F-FMISO PET** context is a *candidate for discussion*, not an available fixed protocol. FMISO imaging can be expensive or difficult to repeat, and PET-derived hypoxia regions can vary materially [1,2]. TCIA head-and-neck **CT/RTPLAN/RTDOSE** collections may support research technical-interface work under their access terms but **do not establish the necessary serial FMISO biological data**, and FDG uptake cannot be substituted as equivalent hypoxia measurement. Without appropriate data and qualified partner access, this indication may be the wrong first commercial target.

Commercialization feasibility needs independent evidence of a real user pain point, user interviews, workflow costs, willingness to pay, and a fair scientific comparator. Novelty needs a prior-art, patent and freedom-to-operate review, not rhetorical assertion. For NCI SBIR/STTR readiness, an eligible incorporated US small-business applicant, compliant PI/employment, a defensible budget, and an institutional workshare with a medically qualified partner are still missing [8,9]. The proposed Curious NerdworX LLC is **not formed**, and no award, purchase or laboratory agreement exists.

**Limitations:** toy fixtures; non-independent ground truth; synthetic biological states; unknown thresholds/calibration; no radiological data rights, real biomarker inference or clinical data; no vendor TPS adapter, dose measurement, human factors or external assessment; narrow comparator heuristics; no controlled clinical use. The current status therefore cannot support any estimate of patient benefit, treatment survival, physical-dose accuracy, reliability or regulatory classification.

## 5. Conclusion

We supply a reproducible software prototype and a falsifiable pre-TPS evidence-qualification decision contract—not a validated radiotherapy product. The immediate next scientific result of value is **independent challenge and interoperability evidence**, followed only conditionally by qualified medical-physics TPS and physical dosimetry. Either a favorable or adverse finding would be a useful result. No clinical progression is justified by these software tests alone.

## References (source checking required before submission)

[1] Sambasivan et al., “Is there a role for [18F]-FMISO PET to guide dose adaptive radiotherapy in head and neck cancer?”, *Clinical and Translational Imaging* 12, 137–155 (2024). https://doi.org/10.1007/s40336-023-00607-y
[2] Welz et al., randomized phase II dynamic FMISO PET dose-escalation study, Radiother. Oncol. (2022). https://pubmed.ncbi.nlm.nih.gov/35395276/
[3] RaySearch Laboratories, RayStation product and robust optimization descriptions (commercial technical baseline; not independent comparative test). https://www.raysearchlabs.com/raystation/
[4] Adaptive radiotherapy end-to-end QA with Ethos, public research. https://pmc.ncbi.nlm.nih.gov/articles/PMC12005670/
[5] ASTRO adaptive-radiotherapy safety white paper. https://pubmed.ncbi.nlm.nih.gov/39424080/
[6] DICOM PS3.3, radiotherapy plan information object definitions (2026b). https://dicom.nema.org/medical/dicom/2026b/output/chtml/part03/sect_C.8.8.9.html
[7] WorldShepherd BAROS source, closed loop/clinical governance/evaluation and regression tests. https://github.com/Bdavis1390/Sara_pro/pull/565
[8] NIH SEED: Understanding SBIR and STTR. https://seed.nih.gov/small-business-funding/small-business-program-basics/understanding-sbir-sttr
[9] NCI Parent SBIR/STTR announcements PA-27-100 / PA-27-102. https://sbir.cancer.gov/small-business-funding/grants/omnibus-solicitation
[10] Wray et al., “Development of 18F-Fluoromisonidazole Hypoxia PET/CT Diagnostic Interpretation Criteria and Validation of Interreader Reliability, Reproducibility, and Performance,” *Journal of Nuclear Medicine* 65, 1526–1532 (2024). https://doi.org/10.2967/jnumed.124.267775

**Editorial release gate:** expert review, references verification, disclosure/IP clearance, citation and methods checks required before presenting as externally reviewed or submitting to any journal.
