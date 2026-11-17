# BAROS Phase 0 data-access gate and biomarker feasibility register

**Date:** 2026-11-16. **Classification:** public-safe planning; no clinical data downloaded; no institutional approval or research partnership secured.

## Decision

Split the proposed HNSCC/18F-FMISO product demonstration into two **non-interchangeable** tracks:

1. **Planning-data interface track (research, no biology):** test DICOM-RT reference/geometry, RTPLAN/RTSTRUCT/RTDOSE reading and validation using a properly licensed and legally accessible RT dataset. This cannot measure performance of biological adaptation or a commissioned TPS's recalculation.
2. **Biological qualification track (conditional):** test actual longitudinal hypoxia measurement quality, identifiability, registration uncertainty, and abstention only once a qualified investigator confirms a legally usable paired FMISO or alternative biologic dataset and approves study-specific interpretation. Synthetic hypoxia values may exercise software interfaces but do **not** validate biologic models.

**No FMISO-to-FDG substitution**: FDG PET uptake is not a direct FMISO hypoxia index and must not be labelled such.

## Candidate collection inventory

| Collection / source | Verified published description | Potential purpose | Access / blocker | Decision |
|---|---|---|---|---|
| TCIA HNC-IMRT-70-33, DOI 10.7937/ahqh-xc79 | 211 patients; planning CT + RTSTRUCT + RTPLAN + RTDOSE; 23.27 GB; one institution and uniform 70 Gy / 33 fraction primary PTV prescription | Research DICOM-reference and plan/dose integrity fixtures, subject to terms | Confirm legal imaging access, distribution restrictions, per-case DICOM linkage and institutional review; **no serial FMISO established** | Candidate Phase 0 technical dataset; not a biologic-adaptation validation set |
| TCIA HEAD-NECK-PET-CT | 298 subjects in imaging table; PET/CT, RTPLAN/RTDOSE/RTSTRUCT present; predominant FDG imaging | Modalities/registration *research* and some DICOM plan checks | NIH controlled access; PET uptake does not establish hypoxia | Conditional technical source, not a FMISO dataset |
| TCIA QIN-HEADNECK | 279 participants, multi-timepoint 18F-FDG PET/CT | Longitudinal PET dataset-transport tests | TCIA restricted license; lacks a verified paired FMISO+RTPLAN/RTDOSE structure for the proposed claim | Not an FMISO validation source |
| TCIA HEAD-NECK-RADIOMICS-HN1 | 137 subjects, CT/RTSTRUCT/PET etc. | Research geometry / annotation QA | Restricted image access, explicit non-commercial terms in collection description; no commercial rights assumed | Avoid for commercial product testing absent license approval |
| Partner-provided serial FMISO | No actual institutional dataset agreement identified | Test signal-specific uncertainty and abstention | Site availability, PET protocol, temporal/registration repeatability, clinical governance, permissible reuse and appropriate RT reference objects remain unknown | **Hard STOP** on biomarker-specific validation until independently confirmed |

## Evidence against premature biomarker positioning

The 2024 narrative review by Sambasivan et al. (PMID 39286295) reports cost/access limitations, inconsistent FMISO repeatability, shifting hypoxic regions and insufficient evidence to support routine FMISO-guided adaptive dose painting in head-and-neck cancer. A 2022 randomized Phase II investigation of FMISO-directed escalation (PMID 35395276) closed early due to slow accrual and found statistically non-significant difference in local control (p=0.150). These are **not BAROS results** and do not establish clinical benefit for our architecture. The fragility of a changing biologic signal is a research motivation for careful abstention, but it is also a major commercial and scientific adoption risk.

## Data-governance checklist before access

- Record dataset version, exact DOI, license, download authorization, permissible research/commercial uses, reuse/publication restrictions, and required citations.
- Confirm whether controlled-access images can disclose facial anatomy; apply TCIA terms and institutional data-security requirements.
- Identify approved dataset owner, patient/privacy governance, whether a human-subjects determination is needed, and whether any future data is PHI.
- Freeze approved minimal DICOM tag allowlist, per-record identity/linkage QC (Frame of Reference UID, RTPLAN/RTDOSE/RTSTRUCT references and geometry), acquisition conventions, units and orientation, and retain any mismatches.
- Redact subject identifiers in public logs, test fixtures, README, error messages and screenshots. Never commit restricted images or PHI.
- If no adequate biomarker data or qualified partner is available, *do not substitute a generic digital twin result and label it clinical feasibility*.

## Proposed go/no-go milestones

**Gate 0A (can begin before a partner):** secure a permitted DICOM-RT research sample; create a reproducible non-clinical plan/structure/dose metadata validation report with exact dataset identifiers, software hashes and negative-control corruption fixtures. This verifies an **interface adapter**, not delivery accuracy.

**Gate 0B:** demonstrate synthetic proposal/abstention correctness with both disqualified and qualified positive scenarios; compare against trigger-only and abstain-all policies, report denominator and statistical uncertainty; no clinical extrapolation.

**Gate 1:** prospective partner confirms one funded/authorized workflow, one case definition, one actual biologic measurement protocol and accessible datasets. A medical physicist freezes acceptable dosimetry/geometry tolerances and conducts independent TPS evaluation.

**Gate 2 (after authorization):** partner runs blinded/held-out review and independent measurement. Any material silent mismatch or attempted clinical authorization by software is a stop.

## References / authoritative collection pages

- https://www.cancerimagingarchive.net/collection/hnc-imrt-70-33/
- https://www.cancerimagingarchive.net/collection/head-neck-pet-ct/
- https://www.cancerimagingarchive.net/collection/qin-headneck/
- https://www.cancerimagingarchive.net/collection/head-neck-radiomics-hn1/
- https://pubmed.ncbi.nlm.nih.gov/39286295/
- https://pubmed.ncbi.nlm.nih.gov/35395276/

**Release gate:** This register is due-diligence design, not a license, a download inventory, confirmation of partner eligibility, or approval to use clinical data.
