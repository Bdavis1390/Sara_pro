# BAROS EvidenceGate — independent clinical-physics feasibility screening packet
**Prepared:** 2026-11-17 | **One-page-style technical intake, NONCONFIDENTIAL / NONBINDING / RESEARCH ONLY**  
**Stage:** prospective partner screening, NOT a signed study, NIH application, clinical protocol or request for patient data.

## Research question for an independent radiation-oncology / medical-physics team

Is there a credible unmet *research planning* need for an independently auditable **pre-TPS biological-evidence qualification and abstention** layer that detects unsupported longitudinal biological inputs before a research adaptation proposal, while avoiding needless rejection of valid cases? Could that be shown using one permitted biological measurement and a version-locked TPS workflow, without introducing unreviewed treatment changes?

**Current technical status:** BAROS development branch implements a fail-closed proposal/hold/fallback decision contract; verifies both prior/current state qualifications, numerical identifiability for a supplied sensitivity matrix, provenance/digest replay, and blinded/paired software-comparator interfaces. All are **developer-authored synthetic software tests**, not an independent clinical model, physical dose or treatment demonstration. Exact CI at 2026-11-17 commit `f6677fdc788d05404d3c5af283edca72a254049c`: 237 bounded research tests passing, two warnings; this is a time-locked internal snapshot only.

**Biological candidate, not a chosen assay:** serial 18F-FMISO PET-derived hypoxia state in head-and-neck radiotherapy. Suitability and dataset availability are unknown; current PET/CT and planning images available elsewhere do NOT establish calibrated serial FMISO, and FDG uptake is NOT interchangeable with hypoxia. The partner may reject this pairing and suggest a better feasible initial use case. No biologically calibrated thresholds exist in BAROS.

## Proposed two-stage non-patient-care scope (for institutional decision)

| Stage | Research-only task | WorldShepherd contribution | Qualified partner controls and evidence | STOP |
|---|---|---|---|---|
| **A — synthetic/interface** | Challenge the software with independently specified corrupted/contradictory biology-state flags and permitted mock DICOM CT/RTSTRUCT/RTPLAN/RTDOSE reference cases | Frozen source/build, test interfaces, sanitized provenance, decision/abstention logs, output-denominator report, reproducible negative cases | Independently defines intended-use and failure taxonomy, generates *new* challenge labels, holds labels before developer response, chooses at least one legitimate comparator; verifies licensed data use | Any unqualified proposal, patient-care authority, identity/dose/geometry mismatch not reported, or unverifiable case custody |
| **B — *conditional* physics feasibility** | Investigate one institution-selected TPS/version, approved mock phantom case and clinical physics acceptance tests | Research-only integration concept and failure-preserving evidence record; no independent clinical plan generation claim | Institution supplies commissioned TPS and equipment under its rules; qualified medical physicist independently sets tolerances, recalculates dose, reviews transfer/geometry and performs any required physical measurement; radiation oncologist assesses clinical relevance | Unauthorized data, unsafe influence on real patient planning, material dosimetry/geometry discrepancy, or failed independent acceptance |

**Clinical commissioning reference, not evidence of BAROS completion:** AAPM MPPG 5.b describes TG-119 mock head-and-neck and C-shape plan/measure/compare checks; it distinguishes those from validation using representative clinical cases and anthropomorphic end-to-end phantom assessments. Institution must independently decide which tests apply, with actual dosimeters and calibrated TPS; no scalar gamma threshold or pass rate is invented by the developer. https://doi.org/10.1002/acm2.13641

## Minimum decision sought from a prospective partner

A brief email response answering: (i) whether this is a clinically relevant unmet *research* problem or already covered by existing checks; (ii) what one **feasible** biomarker/site/technique would be responsibly measurable, and whether the proposed FMISO example should be discarded; (iii) whether there is a legally permitted mock/clinical data path and versioned TPS research environment; (iv) which physical QA and radiation-oncology personnel would need to review it, and an approximate resource category/time commitment if interested; (v) whether an institute could **consider** an SBIR subcontract or STTR research collaboration after its sponsored-research, legal and scientific review. These are exploratory questions, not promises or requests for proprietary methods.

## Boundaries / documentation

- No PHI, patient imaging, medical records or vendor-secret TPS exports requested by this note. Any future human data requires signed rights, institutional governance and appropriate ethics/privacy determinations first.
- No clinical treatment, prescription, dosage or hardware command can be issued by BAROS; final medical authority is institution-only.
- Commercial and regulatory classification is **not** resolved. FDA's January 2026 CDS guidance and digital-health policies must be reviewed function by function before any clinical product claims; a research-only label is not automatically exempt.
- Neither independent review nor a positive clinical measurement establishes novelty, patentability, funding, purchaser demand or regulatory authorization by itself.
- Pre-existing WorldShepherd intellectual property remains with its owner. No license, joint inventorship, confidentiality obligation, institutional association, employment or funded workshare is created by exchanging this nonconfidential packet.
- The applicant entity is not yet formed; no grant proposal or company eligibility is represented as complete. No fees, submissions, clinical samples or contracts are authorized by this packet.

**Supporting draft artifacts:** `docs/baros/BAROS_SHORT_RESEARCH_MANUSCRIPT_2026-11-17.md`, `BAROS_INDEPENDENT_EVALUATION_PREREGISTRATION_TEMPLATE_2026-11-17.md`, `BAROS_FDA_INTENDED_USE_AND_CLAIMS_BOUNDARY_2026-11-17.md`, and draft GitHub PR #565. The long original technical monograph should **not** be sent unsolicited.

**Decision gate:** external investigators first affirm specific interest and advise a bounded scope by email; only afterward consider confidential work, data exchange, funding or a formal agreement. Do not create duplicate outreach or represent interested reviewers as committed collaborators.
