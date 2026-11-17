# BAROS — Independent 18F-FMISO assay and pre-TPS qualification analysis plan (SAP) v0.1

**DRAFT — November 17, 2026. No investigator, IRB, data custodian, nuclear medicine physician, medical physicist, radiation oncologist or sponsor has adopted this protocol. No patient data, clinical plan, institutional datasets or claims of clinical effectiveness are present.**

## 1. Decisions and scope to freeze before analysis

**Target question (conditional, not assumed clinically worthwhile):** For *one independently selected and legally permitted* head-and-neck radiotherapy use case involving **two 18F-FMISO PET observation timepoints**, do acquisition, interpretation, geometry, uncertainty and biomarker-identifiability qualifications detect **research replan proposals unsupported by the biological evidence**, without rejecting an impractical number of genuinely eligible cases, compared with relevant existing research/institutional methods?

The investigator—not BAROS—must decide the disease site/histology, biomarker assay definition, imaging modality/reference region, timepoints, actual planning workflow, baseline comparator, statistical analysis plan version and clinically meaningful endpoints. The study may validly conclude that FMISO is unsuitable, not cost-effective, or fully covered by existing planning safeguards. No prescribed dose, fractionation change, patient-care order, or clinical treatment optimization is in scope.

**Do not equate** (a) interreader agreement, (b) no-treatment scan *test–retest* precision, (c) longitudinal **on-treatment** biological response, (d) predictive clinical utility, or (e) commissioned-TPS dose/deliverability accuracy. They are separate evidentiary propositions requiring different measurements.

## 2. Data provenance and study-level identifiers (all rights OPEN)

At each permitted time point, a secure institution-controlled manifest would record a pseudonymous case/group token; approved local linkage to participant identity only at the institution; study/case IDs and protocol amendment; tracer and activity; injection and scan timing; scanner/reconstruction/attenuation correction version; PET/CT/MRI acquisition and registration provenance; study-specific calibrated uptake/reference metrics; expert reads and adjudication; measurement uncertainty; frame/ROI and contour metadata; any independently held source-digest and attestation; available QA reference; reasons for missingness and protocol deviation.

**No names, MRNs, dates of birth, raw images, private credentials, or vendor-confidential records are to be placed in the public GitHub repository or ordinary email.** Even deidentified image use needs permission; a SHA-256 hash alone is neither authorization nor proof of a trustworthy origin.

Linkage to RTSTRUCT/RTPLAN/RTDOSE or dose-influence matrices must exist **for the same permitted case** before a combined biological–planning study is attempted. **Do not join** independent TCIA, OpenKBP-Opt and Vanderbilt cohorts as if they were the same participants. A planning benchmark without FMISO truth is a *methods* reference only.

## 3. Endpoint definitions and denominator discipline

| Endpoint | Definition; study owner must finalize | Interpretation and caution |
|---|---|---|
| **Reader concordance** | Raw agreement and Cohen/Fleiss kappa (as justified) for independently blinded expert and secondary reads, before/after training only when the institution actually administers a controlled training intervention | Agreement is prevalence-sensitive and not an accuracy guarantee. Record indeterminate/missing reads and CIs. Do not transplant Wray et al.'s reported kappa into BAROS. |
| **Quantitative no-treatment repeatability** | For true test–retest pairs, prespecified within-subject change/bias, repeatability coefficient or limits of agreement and appropriate within-subject variance; specify image registration, reference ROI and tracer variability | A baseline-to-on-treatment pair **cannot** estimate noise-only repeatability without additional evidence/model assumptions. Spatially heterogeneous hypoxia demands voxel/subregion evaluation, not only aggregate lesion volume. |
| **Spatial concordance** | Prespecified repeat-scan overlap/displacement of hypoxic regions (e.g. Dice/Jaccard, centroid shifts and geometrical uncertainty) when a validated segmentation and registration convention exists | All thresholds and reference regions must be expert selected, scanner/version documented, and interpreted with PET resolution/partial-volume effects. No universal cutoff is implemented. |
| **Biological-change qualification** | For a frozen external measurement-error model, fraction of changes with enough supported signal to justify a *research proposal* vs withheld/indeterminate changes; adjudicator-blinded case labels | Such labels are not proof of clinical benefit or safe dose painting. Document assay errors, disagreement and nonidentifiable cases. |
| **Critical false proceed** | Disqualified-trigger cases where the software nevertheless allows a research replanning proposal / **all independently adjudicated disqualified-trigger cases** | Present numerators, denominators, exact/appropriate intervals and all individual severe failures. A zero observed count is **not** zero population risk. |
| **Eligible proposal recall / false abstention** | Eligible research-trigger proposals retained / **all independently adjudicated qualified-trigger cases**; report blocked eligible cases separately | Prevents an always-abstain algorithm from claiming success by suppressing all activity. |
| **No-trigger false proposals** | Proposed reoptimizations / **all independently adjudicated no-trigger cases** | Kept as a separate preregistered stratum, not silently excluded from paired scorer. |
| **Paired comparator discordance** | Same-case difference in proposal decision under BAROS and prespecified quality/OOD or established physics workflow baseline; stratify by independent true label | Match challenge digest, patient/case IDs, thresholds and data partitions; record both BAROS-only and comparator-only failures. Do not select a favorable threshold after unblinding. |
| **Research workflow burden** | Investigator-observed minutes/case, count of unsupported input resolutions, reviewer workload and explainability scores under blinded/defined tasks | Actual user demand, purchaser and workflow value require separate structured interviews; source-only benchmarks do not establish commercial value. |

## 4. Pre-registration and analysis protections

1. Have independent radiation oncologist, nuclear-medicine imaging expert and medical physicist review whether the scientific question merits testing; document disagreement and potential conflicts. They can STOP the proposal.
2. Freeze intended use, tracer definition, scanner and assay normalization, adjudication process, all exclusion/missing-data rules, case splits, comparator implementation, research thresholds and stop rules **before seeing held-out labels**. Record how prospective changes affect sample-size assumptions and analysis.
3. **Split by participant, not scan/voxel:** all images/timepoints/regions from one individual belong to one split; do not count 21 dose predictions for one OpenKBP-Opt patient as 21 independent patients. For uncertainty, resample or cluster at the participant level; report sample size as subjects and as observation pairs.
4. Training/calibration data establish assay-specific thresholds and model uncertainty. The final independent evaluation set is untouched until protocol freeze. Any discovered labeling ambiguity must be reported, not resolved with knowledge of which method appears more favorable.
5. Evaluate missing and unusable scans as an explicit endpoint. Include a flow diagram of screened, included, censored/excluded, missing, adjudicated, qualified and disqualified cases; avoid reporting only easy/high-quality images.
6. For each model/policy report **every predeclared operating point**, exact risk–coverage and abstention tradeoff, severe failures and confidence intervals. A test count or kappa from a paper is **not** a sample size for BAROS.
7. Do not use a convenient fixed number of clinical patients without a partner-owned feasibility/power/precision justification. The previously proposed 100 independent synthetic challenge cases are **Stage A software tests only**; they are not powered patient-level biomarker validation.

## 5. Technical and physical gate, separate from imaging assay

Stage A: test the frozen research API with evaluator-authored synthetic challenges and permitted non-patient planning fixtures. BAROS has **no clinical RTPLAN export**; preserve explicit absent TPS/clinical dose authority.

Stage B (conditional): one selected clinical TPS version and machine/technique, investigator-frozen objective semantics, independently recalculated/physically measured phantom doses where appropriate, certified/calibrated equipment, and externally defined clinical target/OAR constraints. Do not invent a gamma pass threshold or imply that source metadata validation proves dose accuracy. Halt progression for any unadjudicated geometry mismatch, wrong plan association, hard constraint breach or unsafe research proposal.

Stage C (not included in Phase I claims): prospective observation, patient treatment or outcomes would need separate regulatory/ethics/clinical approvals and robust clinical evidence.

## 6. Explicit stop / failure criteria

A qualified evaluator may STOP for data rights unverified, inappropriate IRB/consent status, unidentifiable/missing biomarker, unstable measurement interpretation, no defensible reference truth, cross-patient leakage, mismatched cohort/TPS context, no fair comparator, no independent clinical oversight, a critical false proceed or any attempt to treat software status as radiotherapy authority.

**Accept negative results:** failure to distinguish credible biological change from measurement noise or no market need is a scientifically important result. Do not reframe it as clinical success.

## 7. Current evidence, source limitations and owner sign-off

- Development-only snapshot 2026-11-17: existing BAROS software tests and mock FMISO metadata/reader checks, with **no actual FMISO image processing, human subjects, PET reader qualifications, dose recalculation, or independent site-run evaluation**.
- Published impetus: Wray et al., J Nucl Med 2024, DOI 10.2967/jnumed.124.267775; Sambasivan et al., Clinical and Translational Imaging 2024, DOI 10.1007/s40336-023-00607-y. Wray reports improved trained reader agreement; Sambasivan reviews mixed FMISO repeatability and unproven dose-painting efficacy. **Do not imply these publications evaluated or endorsed BAROS.**
- Candidate longitudinal source: Vanderbilt NCT05996432 (study protocol only; no confirmed licensing or matched DICOM radiotherapy records). Academic objective benchmark: OpenKBP-Opt (2022; **no paired FMISO observations**).
- **Independent SAP owner:** NOT ASSIGNED. **Institution/IRB/data agreement:** NOT APPROVED. **Regulatory intended-use determination:** OPEN. **Funding/participation:** UNCOMMITTED.
- **Protocol acceptance and execution:** Not satisfied until an authorized institution records signed/versioned protocol approval, case/rights custody, investigator-owned analysis and independent decision to proceed. Drafting this file does not satisfy those conditions.

**References:** https://pubmed.ncbi.nlm.nih.gov/39266287/ ; https://pubmed.ncbi.nlm.nih.gov/39286295/ ; https://clinicaltrials.gov/study/NCT05996432 ; https://github.com/ababier/open-kbp-opt .
