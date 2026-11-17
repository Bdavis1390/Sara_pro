# BAROS EvidenceGate: NCI Phase I product-feasibility design (public-safe draft)

**Status:** 2026-11-16; pre-application, non-confidential, **not** a validated medical device or clinical research authorization. Original research reference: `baros-implementation-validation-gate`; this branch is a development candidate, not a clinical release.

## Product, customer, problem

**Candidate product:** BAROS EvidenceGate, a **research-stage pre-treatment-planning decision-qualification module**. It ingests a fixed-schema longitudinal biological state and data-quality/uncertainty information; returns one of **propose for research replanning / hold last valid / fall back to standard / do not adapt**; identifies the disqualifying evidence; and generates a replayable decision record bound to the model configuration and source evidence. It **cannot authorize treatment**. A commissioned TPS, independent dose recalculation, patient-specific QA and qualified human authorization remain external and authoritative.

**First potential buyer/customer to validate:** academic radiation-oncology/medical-physics groups conducting controlled translational studies; future potential buyers include established TPS vendors and care systems, subject to discovery. No purchaser, paid pilot, letter of support, or pricing willingness is yet confirmed.

**Unmet need to test:** whether researchers can reliably prevent unqualified *biological* evidence from silently generating adaptive planning proposals, audit precisely why an adaptation was deferred, and reproduce decisions. This is a proposed market gap, **not yet demonstrated by buyer interviews**.

## Bounded initial use case and intended biological input

- **Indication / treatment:** head-and-neck squamous-cell carcinoma with research photon IMRT planning; one single institution-approved TPS/workflow and release version to be selected and frozen by an actual partner.
- **Candidate biological signal:** serial **18F-FMISO PET-derived tumor hypoxia index**, with uncertainty and registration-quality metadata. Do not substitute FDG PET uptake for hypoxia. Do not assume the required serial FMISO data exists, is accessible, or is fit for clinical adaptation.
- **Decisive feasibility blocker:** confirm legally available, sufficiently paired scans plus associated approved treatment-plan and dosimetric data and an institutional medical-physics team. If this fails, the claim and Phase I study must pause and be rewritten with partner input; changing the biomarker/site/TPS requires a new frozen protocol.
- **Commercial reality:** FMISO is costly and uncommon. Its limited repeatability and evolving uptake may make it particularly relevant for studying *abstention*, but also potentially unattractive for a first market. A partner must adjudicate this tradeoff before any formal application.

## Competitive boundary and putative differentiator

Commercial TPS offerings already include robust optimization and adaptive radiotherapy (for example RayStation and Ethos). BAROS does **not** claim priority over basic adaptive planning, dose optimization, DICOM handling, patient QA, uncertainty assessment, or generic provenance.

**Differentiation to test, not a verified novelty claim:** an external evidence-qualification contract integrating (i) longitudinal biological change and measurement quality, (ii) identifiability and out-of-distribution rejection, (iii) explicit trigger/abstention versus proposal behavior, (iv) evidence-dependency invalidation, and (v) locked, auditable decision provenance **without treatment authority**. Whether any combination is patentable or substantively superior to existing vendor/institutional safeguards is **undetermined**. Conduct an independent prior-art assessment and structured prospective customer discovery before claiming novelty or business advantage.

## Phase I work packages and quantitative decision gates (proposed, not achieved)

**WP0: Eligibility, product discovery and scientific partnership prerequisite.** Legal business applicant, control/ownership, PI employment, workshare and institutional collaboration must be documented for the chosen NIH mechanism. Obtain at least 5 structured potential-user interviews (proposed sample size, not completed), one partner-controlled data/TPS feasibility assessment, and a signed scope/availability statement **before** formal submission. Confirm one biomarker-site-TPS pairing and a viable study cost; if unavailable, STOP.

**Aim 1: Build and qualify a reproducible research EvidenceGate prototype.** Lock intended use, requirements, dataset manifest, safety taxonomy, thresholds, exact dependency versions and source/fixture hashes. Deliver source and binary identifiers, API/schema, event-level decision log, negative-case corpus and executable tests.

- **Predeclared critical pass/fail:** zero *permitted proposals* for all predeclared disqualifying synthetic fixtures; any critical false-proceed or grant of treatment authority is a **STOP**, even if overall test pass rate is high.
- **Counterbalancing endpoints:** false abstention, missed eligible proposal, time per decision, decision coverage and reason-code accuracy. Report denominators and uncertainty intervals; do not optimize only to abstain always.
- **Reproducibility:** every test has stable fixture and software hashes and is reproducible in a clean pinned environment. No claim that synthetic case independence or population safety follows from the test count.
- **Baseline comparison:** ungated research logic with otherwise identical inputs and triggers, plus an anatomy-only/adaptation policy where methodologically relevant. Clinical reference plans are **not** replaced.

**Aim 2: Partner-controlled interface and physical/planning feasibility (conditional).** Only after Aim 1 critical gates, exchange research outputs with one partner-selected commissioned TPS/recalculation workflow under a governed agreement. Independent clinical physicists verify RT DICOM geometry and reference semantics, dose scaling, constraint interpretation, plan exchange, selected negative controls, and end-to-end phantom testing as required by the partner. Quantify failed exchanges, silent mismatches, hard constraint breaches, physically measured dose differences, QA status and turnaround time. Study-specific numerical tolerance thresholds must be frozen **by the independent physicist** rather than invented here. Any clinically material silent dose/geometry defect is STOP.

**Not in this initial funded scope:** retrospective evidence of patient outcome benefit, prospective shadow-mode deployment, adaptive treatment delivery, interventional clinical study, FDA clearance, dose painting outcome claims, or clinical reliability percentages. Such steps require separate approvals and evidence.

## Evidence checkpoint: what already exists

An existing hosted BAROS research workflow at 2026-11-08 tested 82 bounded software tests (two warnings) and 1,000/1,000 synthetic bounded acceptance cases. The main product code includes `decide_adaptation`, model qualification, and governance/evidence gates. **Internal software verification only.**

An updated software-boundary verification at frozen commit `d1dfd1f7936991c506f5904fa9b56fabc5d06926` reports **258 passing bounded tests, two warnings and successful required GitHub workflows**. Tests include 1,024 combinations of two-timepoint qualification flags, blinded challenge and entropy/MI reference calculations, and the **synthetic-only abstract biological-to-priority adapter** at `baros/research_objective_intent.py`. Its dimensionless output is NOT a clinically valid objective/TPS adapter, prescribed dose, clinical plan or treatment authorization. Tests remain developer-authored and should not be called independent evidence.

**Still missing:** independent negative corpus, fixed biological biomarker interpretation and calibration, partner-approved data access, independent TPS testing, phantom measurements, medical physicist adjudication, comparative utility and buyer discovery, a verified eligible small-business applicant and required registrations (a legitimate sole proprietorship may be an option), and institution-approved workshare.

## Regulatory and independent-physics feasibility gate (added 2026-11-17)

**FDA scope cannot be inferred from this prototype.** The current product is explicitly limited to research-only pre-TPS decision qualification. FDA's January 2026 Clinical Decision Support final guidance applies function-specific criteria; FDA Digital Health guidance identifies patient-specific radiation dosage planning among potentially regulated device software functions. Human sign-off, lack of direct dose delivery and saying 'research-only' do NOT automatically exempt a future commercial patient-specific module. A qualified device regulatory assessment is required before commercial clinical claims or integration. See `BAROS_FDA_INTENDED_USE_AND_CLAIMS_BOUNDARY_2026-11-17.md` and the FDA sources linked there.

**Independent partner candidate packet:** `BAROS_INDEPENDENT_PHYSICS_FEASIBILITY_SCREENING_PACKET_2026-11-17.md` defines Stage A synthetic/phantom research interface tests and conditional Stage B partner-owned commissioned TPS plus physical dosimetry. AAPM MPPG 5.b identifies TG-119 mock head-and-neck and C-shape plans for planning/measurement QA, *not as a substitute for clinical commissioning or end-to-end independent measurements*. **No physics partner, licensed data path, hospital TPS access, actual dose comparison or approved protocol has been secured.** Do not count drafting this packet as an interview, letter of support or external validation.

**Go/no-go addition:** No SBIR/STTR submission should claim a regulated or exempt clinical product without a written intended-use and regulatory review rationale, a feasible external validation plan and documented commercialization hypothesis. This regulatory uncertainty belongs in the feasibility risk and workplan, not hidden from reviewers.

## NIH mechanism / eligibility

Current NCI parent routes include `PA-27-100` (SBIR) and `PA-27-102` (STTR); these are *funding announcements*, not awards or acceptance. Next standard due date shown as **2027-01-05**. No application is ready to file.

- NIH SBIR Phase I: generally at least two-thirds of the research effort at the applicant small business; primary PI employment with the company.
- NIH STTR: eligible small business performs at least 40% and a qualified nonprofit research institution at least 30%; PI can be employed by either as NIH permits. IP and workshare need separately agreed contracts.
- An **unformed LLC cannot itself be represented as a formed applicant**, but NIH's March 2026 eligibility policy lists a genuine qualifying **individual proprietorship** as a permitted small-business legal form. The sole-proprietorship path is **unverified**, and both that path and a user-authorized future LLC path require compliant ownership/control, registrations, PI and workshare evidence. No application, filing, grant, clinical data request, contract or institutional commitment is submitted or secured. See `BAROS_PHASE0_CUSTOMER_AND_ELIGIBILITY_GATES_2026-11-17.md`.

## Decision questions for independent review

Does the proposed **product and buyer** address a real actionable unmet need beyond existing TPS safety features? Is FMISO-based HNSCC research an appropriate and available first feasibility context, or should the project stop until an institution proposes a better one? Are the critical failure conditions and independent TPS measurement conditions adequate for a *preclinical* feasibility stage? Is an STTR workshare realistic given the eligibility and IP prerequisites?

## Reference sources (public)

- NIH SEED eligibility/program design: https://seed.nih.gov/small-business-funding/small-business-program-basics/understanding-sbir-sttr
- NCI current parent announcements: https://sbir.cancer.gov/small-business-funding/grants/omnibus-solicitation
- RayStation baseline: https://www.raysearchlabs.com/raystation ; https://www.raysearchlabs.com/robustness-in-treatment-planning/
- Ethos clinical QA (public research): https://pmc.ncbi.nlm.nih.gov/articles/PMC12005670/
- FMISO/HNC limitations: https://pubmed.ncbi.nlm.nih.gov/39286295/
- Head-neck planning baseline (access constraints): https://www.cancerimagingarchive.net/collection/hnc-imrt-70-33/

**Intellectual-property / governance:** documentation is nonconfidential and exploratory. Any data sharing, sponsorship, ownership/license transfer, human-subjects work, regulatory pathway or institutional collaboration requires separate documented authorization. No source-control test or reviewer comment enables patient-care use.
