# BAROS EvidenceGate — NCI Phase I Product Specific Aims v3 (draft for reviewer/partner input)

**2026-11-17 | NONCONFIDENTIAL | NOT SUBMITTED | NOT CLINICALLY VALIDATED | No customer, academic partner, FDA status, or grant award secured.**

## Proposed product and unmet need

**Product for feasibility development:** BAROS EvidenceGate, an **auditable, research-only biological-evidence qualification module** that prevents poorly supported longitudinal biological inputs from silently becoming adaptive-radiotherapy planning proposals. Its potential first users are radiation-oncology medical-physics/translational planning research groups. Whether these groups need or would pay for the product **has not been established**; existing adaptive TPS and uncertainty/QA methods may already solve most of the problem.

**Initial research context to confirm:** head-and-neck squamous-cell carcinoma, research photon IMRT planning, and **one** prospectively chosen biological input. Serial 18F-FMISO PET hypoxia index is a *candidate*, not an agreed or reliably accessible assay. One independent institution must select its actual commissioned TPS, version, machine/technique, available permitted sample and medical-physics lead. **No TPS has been selected or integrated.** If no viable paired biomarker/RT dataset exists, STOP or revise this use case openly; do not substitute FDG uptake as measured hypoxia.

**Putative innovation (unproven):** a frozen, longitudinal evidence contract combining source-bound state, both-timepoint qualification, local model-identifiability failure, uncertainty/OOD and geometry controls, an explicit reasoned abstention/hold decision, integrity-bound replay and **non-authoritative research planning priority intent**. BAROS does **not** claim to invent uncertainty assessment, robust optimization, QA, adaptive planning, logging or medical human oversight. Novelty and commercial superiority remain empirical questions.

## Commercial feasibility milestone (before claiming a market)

Complete **five independent structured discovery interviews** across clinical physics, oncology, dosimetry, informatics and a TPS purchaser/vendor; record current alternatives, exact failure costs, user demand, workflow and price objections. Seek at least one nonbinding expression of interest in a properly scoped *research evaluation*. An interview, email acknowledgment or proposed product does not establish a paying customer or a committed collaborator. If no actionable buyer problem is identified, **STOP the present commercial claim**.

## Aim 1 — Build a bounded EvidenceGate prototype and quantify software feasibility

**Deliverable:** versioned research API from frozen input schemas (two observed states, biomarker/measurement uncertainty, geometry, provenance and policy) to **permit / hold / fallback / no adaptation**, explanation and replay record. An optional synthetic planning-intent adapter can show bounded **dimensionless** regional preference changes for approved *research cases only*; it has **no RTPLAN export, prescription/fractionation, machine commands, physical dose engine or treatment authority**.

**Current background evidence:** as of GitHub commit `d1dfd1f7936991c506f5904fa9b56fabc5d06926`, internal CI reported 258 passing bounded research software tests and two warnings. Included tests use synthetic inputs, negative cases and developer-authored comparators. These are engineering verification, not clinically calibrated biological measurements, statistical patient safety or vendor superiority.

**Proposed independent success rules (to be finalized before independent case release):** freeze source and dependency hashes, protocol, thresholds, case strata, blinded labels, error severity and predeclared baselines. A qualified external evaluator supplies **at least 100 new, independent synthetic/phantom-derived challenge cases** spanning critical failure families; no permitted reoptimization for an independently adjudicated disqualifying input and no grant of treatment authority. Record qualified-case recall/false abstention, risk–coverage, false proceed, latency, full denominators and uncertainty intervals. A zero-event count is not zero clinical risk. Any critical fail-closed bypass is **STOP**. The sample count is a design proposal, not agreed or achieved.

**Comparator requirement:** include a genuine uncertainty/OOD method reasonably applicable to the chosen study, plus trigger-only and abstain-all controls. The existing developer-authored quality-only heuristic and reference entropy/MI formulas are **not** a faithful reproduction of a published clinical model; any favorable toy comparison is excluded from claims of superiority.

## Aim 2 — Demonstrate conditional research TPS-interface and dosimetry feasibility

**Prerequisite:** a permitted dataset, signed institutionally reviewed study scope, qualified radiation oncologist and medical physicist, and a frozen TPS/version/machine technique, biomarker and objective translation. **No such partner, access, or TPS commitment exists now.**

Independent physicists will define all RT DICOM geometry/dose/structure criteria; adjudicate plan/constraint mismatches; and, if appropriately supported, perform partner-controlled commissioned TPS dose recalculation, mock-phantom measurements and deliverability QA, with predeclared tolerances. BAROS never overwrites an approved plan or makes a patient-care decision. **Any silent material semantic, geometry, hard-constraint or physical dose discrepancy is STOP.** In a Phase I proposal, physical evaluation is bounded to the institution-approved feasibility subset, not broad patient studies.

**Not proposed:** prospective shadow-mode deployment, clinical plan adaptation, treatment delivery, patient outcomes, FDA clearance, asserted clinical performance percentage, or a patient-level biologic effect claim.

## Applicant, regulatory and funding readiness

- **Applicant form:** the contemplated Curious NerdworX LLC is not formed. NIH's March 2026 Grants Policy Statement permits an eligible **individual proprietorship** as a legal form of small business; that is a possible diligence path, **not an eligibility determination**. The organization must satisfy U.S. small-business status, ownership/control, applicant registrations, and the exact award/NOFO requirements. Do not file, pay, register or contract without approval.
- **Likely workshare to evaluate:** NIH STTR (PA-27-102) if the academic partner must own substantial R&D, with **at least 40% SBC** and **30% research institution** effort and compliant PI affiliation; or NIH SBIR (PA-27-100) if the business can conduct at least two-thirds of Phase I R&D and meet PI primary-employment requirements. Actual workshare, budget, background IP and publication rights require mutually negotiated institutional documents.
- **Regulatory gate:** future patient-specific treatment-planning influence may be regulated medical-device software. FDA's 2026 CDS guidance does not confer exemption merely because a human reviews outputs or the prototype is research-only. Obtain function-by-function regulatory analysis before clinical commercialization claims.
- **Date gate:** listed standard NIH receipt date January 5, 2027. No submission should be promised without the independent partner, legally eligible applicant, feasible study, budget and user authorization.

## Explicit requests for independent technical review

1. Is the putative biological evidence-qualification product clinically meaningful **beyond existing vendor/institution QA**? What result would falsify this?
2. Is serial FMISO-PET suitable and realistically accessible, or should one *other* biology/indication pairing be selected by the institution?
3. Which single TPS/version and mock-case/phantom methodology could be used under lawful access, and what clinical/physics resources would be needed?
4. Is this Phase I scope realistically achievable under a formal STTR (or SBIR) partnership with a genuinely differentiated product and eligible applicant?

**Source references:** NIH SBIR/STTR program overview https://seed.nih.gov/small-business-funding/small-business-program-basics/understanding-sbir-sttr ; NIH 2026 eligibility policy https://www.grants.nih.gov/grants/policy/nihgps/HTML5/section_18/18.5.2_eligibility.htm ; NCI active parent announcements https://sbir.cancer.gov/small-business-funding/grants/omnibus-solicitation ; BAROS research code and evidence gates https://github.com/Bdavis1390/Sara_pro/pull/565 .

**IP:** pre-existing BAROS/WorldShepherd IP remains with its owner; no license, rights transfer, institutional commitment, signed workshare or permission to use clinical data is created by this draft.
