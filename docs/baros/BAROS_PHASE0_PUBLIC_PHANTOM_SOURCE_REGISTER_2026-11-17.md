# BAROS Phase 0: non-patient phantom and public reference-data candidates

**2026-11-17 | Non-clinical technical research only.** No patient or phantom dataset was downloaded or reviewed, and no licensed third-party source was integrated into the product. A public download link is **not** a blanket permission to redistribute, commercialize, or relicense data. Independent TPS physics/calibration remains an open requirement.

## What this work can and cannot prove

**Can test:** bounded DICOM-RT parsing and geometry/reference consistency under externally sourced test structures, synthetic RTPLAN/RTDOSE fixtures, adverse-file corruptions and reproducibility.

**Cannot test by itself:** clinically correct measured dose, biological hypoxia-state quality, patient outcome, treatment deliverability, commissioned TPS results, vendor interoperability, regulator approval, or a physician's safe clinical workflow. Self-generated synthetic cases are useful software verification but must never be counted as independent physics validation.

## Candidate source A — AAPM TG-119 IMRT commissioning mock cases

AAPM TG-119 provides mock clinical cases for benchmarking IMRT planning and QA; published instructions describe the test-suite phantom, targets and normal tissues, and option for DICOM CT and RT structure sets. Important: the published materials do not mean BAROS can assume unrestricted redistribution or commercial rights. Verify current AAPM usage conditions and case-specific metadata before any import. The mock case is **not** equivalent to institution-commissioned TPS or physical phantom dose.

- AAPM report catalogue: https://www.aapm.org/pubs/reports/tree.asp
- Instructions: https://www.aapm.org/pubs/tg119/TG119_Instructions_102109.pdf
- Reference article: https://doi.org/10.1118/1.3238104

Proposed first evaluation: validate controlled RTSTRUCT/CT identity linkage, structure UID references and geometry, then run existing test-suite negative corruptions. Do **not** invent or infer any RTPLAN or RTDOSE values absent from the downloaded files.

## Candidate source B — AAPM MPPG-TPS example datasets

AAPM's external-beam TPS commissioning/QA resource page lists six sample DICOM CT / RT Structure Set datasets, including a **head-and-neck simultaneous integrated boost** case. These can be considered for technical interoperability after checking permitted use and exact file contents; the page does not represent independent BAROS medical physics acceptance or an available institution's TPS.

- Resource page: https://www.aapm.org/pubs/MPPG/TPS/
- Case 5 head & neck, linked from that page.
- The guidelines call for dose comparisons and independent measurements on a properly commissioned system; neither is provided by BAROS source tests alone.

## Candidate source C — public synthetic DICOM generation

RaySearchLabsPublic/dicomutils documents building **synthetic** CT, MR, PET, RTSTRUCT, RTDOSE and RTPLAN objects. A scan of likely top-level license files (LICENSE, LICENSE.md, COPYING) did not locate one. Do not copy, redistribute or integrate its software without verifying actual applicable licensing and provenance. A generated synthetic file is not a vendor-certified dose or evidence of real patient accuracy.

- Project: https://github.com/RaySearchLabsPublic/dicomutils

Alternative: continue our existing self-authored, patient-free DICOM test fixtures and negative controls. Any newly introduced third-party dependencies require dependency provenance/security and license review.

## Pre-download/ingestion gate checklist

1. Identify the **actual test case** and scope (phantom or research example, not patient). Verify privacy and possibility of embedded face/patient identifiers. No PHI, MRNs or realistic person-identifying metadata in public CI.
2. Record source/version/license/download terms with unambiguous redistribution, derivative, commercial and publication rights. When unclear, request written permission; do not treat GitHub public visibility as a license grant.
3. Record case DICOM SOP classes, referenced FrameOfReferenceUID, RTSTRUCT/RTPLAN/RTDOSE sequences actually present, acquisition orientation and dose-scaling metadata. Do not assume sample CT/structures include calculated plan/dose files.
4. Define metadata and file hash manifest, reproducible scanner/reader version, exact expected negative mutation cases and rejection criteria. No uncontrolled file execution.
5. Keep any permitted third-party files outside public CI until rights and privacy are settled. Test with our self-authored generated samples in the meantime.
6. All physical dosimetry, TPS-acceptance tolerances, machine/beam models, instrument calibration and scientific interpretations must be **defined and owned by an independent licensed medical-physics partner**.
7. Only mark an actual-ingestion criterion complete after the artifact is received lawfully, SHA256 inventoried, inspected by designated staff and validated. This document is NOT evidence that the case has been ingested.

## Current disposition

- Patient-free software parser/negative tests already exist and pass internal CI.
- External mock phantom dataset **candidate sources identified**, permissions and test-case inventories still to be checked.
- TCIA HNC-IMRT images remain NIH-controlled; the AAPM candidates above do not confer access to TCIA data.
- Neither 18F-FMISO hypoxia observations nor a clinically measured or approved biological adaptation protocol is available.
- A qualified independent collaborator is still required to turn any structural test into a credible external technical evaluation.
