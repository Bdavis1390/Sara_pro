# BAROS serial-FMISO measurement feasibility: independently supervised candidate

**Date:** 2026-11-17. **NONCONFIDENTIAL RESEARCH OPPORTUNITY — NOT AN ACCESS GRANT, COLLABORATION, DATASET OR APPROVED PROTOCOL.**

## Independent study source identified

The NCI trial registry publicly describes Vanderbilt University/Ingram Cancer Center study **NCT05996432** / NCI-2023-04830, *MRI and 18F-Fluoromisonidazole PET/CT Scan for Assessing Tumor Hypoxia and Guiding Adaptive Radiation Therapy in Patients With Head and Neck Cancer or Brain Metastases*. As of the registry view checked November 17, 2026, the trial page lists it as **active** and reports that its head-and-neck population undergoes MRI and 18F-FMISO PET/CT at screening and again **7–14 days into standard-of-care radiotherapy**. The public study objective is to validate MRI markers against FMISO-defined tumor hypoxia and measure treatment-related changes, not to validate BAROS or supply an automatic planning TPS interface.

- Authoritative trial page: https://www.cancer.gov/research/participate/clinical-trials-search/v?id=NCI-2023-04830
- Trial identifier: https://clinicaltrials.gov/study/NCT05996432
- Listed institutional lead: Vanderbilt University/Ingram Cancer Center.
- **Research inquiry actually sent 2026-11-17** to the official study-listed contact, asking about feasibility, whether medically valid longitudinal measures exist and only the *institutionally approved route* for potential future de-identified research access. The send was verified through Gmail. No patient data, institution documents, equipment, clinical access, commitment or funding was requested or received.

**DO NOT infer** that trial data are available, that paired DICOM RTPLAN/RTDOSE exist, that the measurement is sufficiently calibrated for BAROS, that sample size/power is adequate, or that the investigator would permit a commercial product study. If the contact declines, records cannot be shared, or the biomarker fails scientific fit, the candidate is a STOP or hypothesis revision.

## Candidate bounded scientific question (not investigator-approved)

Can a frozen, auditably qualified **change** in a serial 18F-FMISO PET-derived research hypoxia measure be classified as eligible versus ineligible to *propose* a planning-intent review, given two time points' independent acquisition, registration, identifiability, out-of-distribution, measurement-quality and uncertainty checks?

This is **not** a proposal to prescribe dose escalation, update treatment plans, interpret patient safety, change clinical care or recalculate physical dose. No FMISO signal is being mapped to a clinical Gy value or fractionation change.

## Mandatory metadata and rights questions before study design

Only an authorized investigator may determine these; none is confirmed.

1. **Study scope and timing:** one head-and-neck indication, baseline and day 7–14 imaging, actual radiotherapy technique and available TPS/version **if any**; site-specific protocol amendments and trial status must be checked.
2. **Biological definition:** validated tumor/hypoxia regions, tissue-to-blood or tissue-to-muscle ratio definitions as applicable, tracer uptake/decay/scan timing, normalizations, repeatability and threshold-setting process. Do not choose a universal FMISO cutoff from another paper without clinical adjudication.
3. **Image/plan identity:** any legal paired CT/MRI/PET registration, FrameOfReferenceUID, structure references, plan/dose identities, motion and temporal drift; explicitly record missing RTPLAN/RTDOSE instead of inventing them.
4. **Data governance:** institutional protocol and data custodian, consent, ethics/IRB and HIPAA determinations, permitted secondary/commercial research, DUA/MTAs and publication restrictions, permitted de-identification and security/storage; no raw images or patient identifiers in public GitHub or unencrypted email.
5. **Analysis independence:** clinician/physicist-specified truth labels, held-out cases, calibration population, method comparison, timepoint and artifact freeze and negative-result publication rights. The original trial is not necessarily powered for this separate BAROS software question.
6. **Feasibility stop:** unavailable serial images, unstable hypoxia measurement or registration, inadequate independence, incompatible plan context or prohibitive rights/cost -> change biomarker or stop; do not treat FDG uptake as an equivalent hypoxia value.

## Relationship to other datasets

- TCIA **QIN-HEADNECK** is longitudinal **FDG-PET**, not a proven FMISO source.
- TCIA **HNC-IMRT-70-33** supplies planning CT/RTSTRUCT/RTPLAN/RTDOSE, but images are NIH controlled access and the cohort is NOT a longitudinal FMISO assay.
- **OpenKBP-Opt** is an academic head-and-neck IMRT *dose/fluence/objective-weight* reference, not longitudinal biological imaging, not commissioned TPS and not a partner clinical plan QA.
- Do **NOT** join persons or dose records across independent cohorts and imply case-level biological/TPS validation. Cross-dataset tests may prove schema handling only.

## Go/no-go statuses

| Evidence | Current result |
|---|---|
| A legitimate registered protocol uses serial FMISO imaging in head-and-neck RT | **Yes — registry evidence only** |
| Official listed research contact approached once, with safe data-governance limits | **Yes — inquiry sent, no reply yet** |
| Scientific suitability/assay repeatability reviewed by investigator | **OPEN** |
| Consent, rights and deidentified datasets approved for any BAROS use | **OPEN** |
| Case-level paired RT planning/structure/dose data and a version-locked commissioned TPS | **OPEN** |
| Independent clinical challenge, measurement and meaningful biological threshold | **OPEN** |
| STTR/SBIR partnership, workshare, IP or funding | **OPEN** |

**No patient-level study, clinical pilot, medical device claims, institution-controlled measurement or data transfer has occurred.**
