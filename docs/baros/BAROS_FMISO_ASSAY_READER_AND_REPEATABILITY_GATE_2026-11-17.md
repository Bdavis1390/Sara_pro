# BAROS serial 18F-FMISO biological-evidence validation — assay and reader protocol v0.1

**November 17, 2026 | NONCLINICAL planning draft, not an institutional/IRB-approved protocol or evidence of any patient measurement.** This addresses the biological-input, quantification, temporal-reproducibility and falsifiability requirements identified in scientific review. No Vanderbilt, MSK, UNC, Duke or other institution has accepted this protocol, supplied data, or agreed to collaborate. No patient images or medical identifiers were imported.

## Scientific evidence motivating additional qualification

**Wray et al., J Nucl Med 2024, PMID 39266287, DOI 10.2967/jnumed.124.267775:** 123 patients in an HPV-positive oropharyngeal-cancer study contributed 134 FMISO PET/CT scans for interpretation. Four less-experienced readers were compared with an expert reference. Following dedicated interpretation training, agreement improved from fair `κ=0.34` to `κ=0.86`; sensitivity and specificity also improved. An estimated **SUVmax ratio >1.2** was examined as a *study-specific* quantitative criterion; **do not apply it as a universal BAROS hypoxia threshold**. Expert label, clinical truth, individual image intensities and patient data are not available to BAROS from this publication. The result shows reader training and interpretation protocol can materially affect declared hypoxia status.

**Sambasivan et al., Clinical and Translational Imaging 2024, DOI 10.1007/s40336-023-00607-y, PMID 39286295:** Literature through November 2023, 40 selected publications, reported inconsistent FMISO repeatability and changes in hypoxic-region location, scarce broad independent evidence for FMISO-guided clinical dose painting, and cost/access burdens. Some short-interval test–retest scans without intervening therapy disagreed spatially even when aggregate hypoxic volume was similar. This undermines a simplistic one-scan, one-threshold, static dose-target approach.

**Critical distinction:** the publicly registered Vanderbilt study NCT05996432 considers a baseline and **on-treatment** FMISO/MRI time point. Such pairs may capture real treatment-induced biological change *plus* measurement and registration variation; they are **NOT, by themselves, a no-treatment test–retest dataset**. Independent assessment of measurement repeatability requires an appropriate separate repeatability experiment, external validated reproducibility model, or statistically defensible partner-selected method before claiming a biological change exceeds noise.

## Three layers BAROS must not confuse

1. **Assay measurement and provenance (NOT implemented clinically):** qualified FMISO tracer, standardized uptake protocol, scan timing after tracer injection, PET attenuation/reconstruction settings, scanner/calibration/harmonization, reference ROI and tumor ROI definitions, decay/activity/normalization and permission/legal custody; CT/MRI registration with frame-of-reference and motion/deformation handling. The hypoxia signal can use partner-chosen normalized measures, but **no universal threshold or radiobiological Gy mapping is adopted here**. FDG or T2* MRI is not a drop-in FMISO substitute.
2. **Interpretation reliability (software metadata screen implemented synthetically):** at each time point, require a locked read/quantification protocol, **two distinct declared synthetic readers**, concordant positive/negative or hold on disagreement/indeterminate; demand declared reader training and registration review. These are deliberately conservative **developer-chosen mock criteria**, not an NCI/FDA/clinical guideline and **not proof that readers exist or were trained**. An independent institution must define valid reader staffing, adjudication and error metrics before real evaluation.
3. **Biological inference and planning meaning (OPEN):** decide whether the measured temporal change exceeds assay noise, distinguishes treatment effect from temporal drift, is biologically identifiable in the chosen model, and is relevant to any clinical objective. Even perfectly agreeing readers do **not** prove spatially accurate hypoxia, a patient benefit, a safe dose increase, or a legally permitted TPS adapter.

## Implementation and direct research-only boundary

`baros/fmiso_interpretation_gate.py` defines strictly **synthetic** evidence metadata with:
- exact tracer token `18F-FMISO`, per-timepoint SHA-256 image fingerprints and frozen acquisition/quantification/reference-frame digests;
- unique, clearly synthetic study and reader tokens, strict advancing phase indexes, two declared reads per phase, independently reviewed registration **as asserted by the test fixture**, reader training **as asserted by the fixture**;
- block on reuse of an image digest as a purported separate serial observation, differing study, mismatched protocol/reference, reader disagreement, unknown/indeterminate read, missing declared training or unreviewed registration;
- a wrapper that permits the existing synthetic abstract priority-intent mapping **only after** mock assay-eligibility and model-input qualifications. On disqualification it produces no priority, no planning proposal and no export/clinical authority.

`tests/test_baros_fmiso_interpretation_gate.py` uses invented samples **only** to exercise the contract. Source hash and training flags are **unauthenticated statements**, not evidence of image authenticity or professional competency. Its `independently_validated=False` output is unconditional by design. This module **does not** read a PET DICOM or infer a tumor voxel, estimate tracer variability or validate the biology-state values supplied by another developer.

## Minimum independent study acceptance design (to be set by qualified investigators)

**Prerequisites:** specific disease site and histology; one institution-approved PET protocol and tracer; at least one expert nuclear medicine reader and appropriate blinded independent interpretation; one quantification definition, patient cohort/timepoint plan and legitimate source rights; qualified oncology/physics lead; version-locked plan/dose handling if applicable; separate ethics/privacy/COI determinations. No externally imposed protocol is assumed.

**Freeze before held-out reading:**
- training/calibration cohort vs untouched patient-level held-out cases (all scans of one patient in only one split), instrument/scanner and acquisition variability; who adjudicates discordance; prospective or retrospective licensing and permitted commercial use;
- true short-interval test–retest/no-treatment repeatability *if available* or independently documented external measurement-error model, separate from on-treatment change analysis;
- spatial hypoxia overlap/displacement/volume stability, uptake quantification and interpretation disagreement; required precision intervals and reasons for missing reads;
- biomarker-based false-proceed, eligible-case false abstention, failure explanation and operator review time under a realistic published-method comparator; definition of independence and case denominators;
- exactly what remains a *research intent*, not a Gy/dose or target prescription, and what constitutes immediate stop before any TPS interaction.

**Do not specify an arbitrary numerical clinical cutoff** (kappa, lesion ratio, PET noise, uptake/registration difference, gamma pass, minimum benefit) without a pre-agreed site-specific rationale. A preliminary proposal to use 100 new developer-independent synthetic challenge cases for software-stage testing **cannot** substitute for a powered patient-level calibration/repeatability study.

**Stop conditions:** data use not authorized, paired FMISO unavailable, different tracer, untrustworthy reference read, quantification protocol drift, unresolved disagreement/missing read, unassessed scan reproducibility, unapproved registration, unable to disentangle noise from real treatment response, false claim of clinical dose validation, or any apparent patient-care authorization.

## Reviewer-facing bottom line

**Engineering question partially answered:** software can now reject badly documented *synthetic* serial FMISO evidence rather than accept unqualified biological inputs blindly.

**Scientific question remains unanswered:** whether a real measured hypoxia change is sufficiently repeatable, reliably interpreted, identifiable, useful beyond existing PET/QA methods and applicable to a commissioned planning workflow. This requires **independent nuclear medicine, radiation oncology and medical physics investigators and licensed data**. If unreproducible or commercially impractical, reject FMISO as the first product input; do not relabel FDG as hypoxia.

**Sources:**
- https://pubmed.ncbi.nlm.nih.gov/39266287/ ; https://doi.org/10.2967/jnumed.124.267775
- https://pubmed.ncbi.nlm.nih.gov/39286295/ ; https://doi.org/10.1007/s40336-023-00607-y
- https://clinicaltrials.gov/study/NCT05996432

**No patient data, images, medical treatment, clinician validation or legal right to datasets are asserted.**
