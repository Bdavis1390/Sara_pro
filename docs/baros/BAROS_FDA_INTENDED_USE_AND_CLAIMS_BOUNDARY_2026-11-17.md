# BAROS EvidenceGate — FDA intended-use and claims boundary screen
**Status:** internal regulatory-readiness / research design only. **2026-11-17.** **NOT** an FDA classification, legal opinion, medical device registration, QMS certification, authorization, or FDA correspondence. No clinical use is permitted by this document.

## Regulatory issue that must be resolved

BAROS is presently an external, synthetic, **pre-treatment-planning research decision eligibility** component. It permits a proposed *research* reoptimization only when both longitudinal input states satisfy evidence/geometry/model-quality criteria; it can abstain/hold/fallback, hashes input and decision metadata, and cannot grant patient-treatment authority. It has no validated TPS interface, no independently validated biological assay, no dosimetry authorization, no drug or radiation prescription output, and no clinical deployment.

But the intended **commercial** purpose cannot be assumed nonregulated from these current technical boundaries. FDA's January 2026 final Clinical Decision Support guidance concerns function-by-function exclusion criteria; FDA's Digital Health Policy Navigator explicitly identifies **software using patient-specific parameters to calculate radiation treatment dosage or create a radiotherapy dosage plan**, as well as **radiotherapy planning software**, among examples potentially subject to active FDA device oversight. A system that indirectly gates or supplies biological planning objectives may also influence treatment. The fact that a human signs off and the present prototype says 'research only' **does not prove exemption**. Regulatory status depends on intended use, marketing claims, actual features, workflow, risk and relevant FDA policy.

**Authority:** FDA, Clinical Decision Support Software final guidance, January 2026: https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software ; FDA clinical decision support FAQs: https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs ; FDA Digital Health Policy Navigator Step 7: https://www.fda.gov/medical-devices/digital-health-center-excellence/step-7-does-device-software-functions-dsf-and-mobile-medical-applications-mma-guidance-apply

## Function-by-function intended-use and claims register

| ID | Bounded function or proposed future functionality | Current state | Regulatory/clinical implication to investigate | Gate |
|---|---|---|---|---|
| F-01 | Parse strictly typed longitudinal *synthetic* biology-state vectors, quality flags and provenance digests | Research code exists | Numerical calculation alone does not determine product device status; medical purpose still matters | Research-only use restriction; no PHI |
| F-02 | Qualify **both** prior and current states (identifiability/uncertainty/geometry/OOD); propose research-only or abstain | Synthetic code and tests; unvalidated biologic model | If offered for real patient adaptive treatment, may affect medical decision; assess as its own function | No clinical decision claims |
| F-03 | Record last-valid identity, hold/fallback and SHA-256 integrity metadata | Software only; digest is **not** authentication | Audit logging does not confer clinical safety or exemption | No authoritative plan change |
| F-04 | Compute predictive entropy and mutual information from supplied stochastic class probabilities | Mathematical reference only, no trained clinical model | No inference of tumor hypoxia or device classification from math alone | Do not call this a validated model |
| F-05 | Read research DICOM-RT objects and check reference/geometry structure | Existing synthetic DICOM code | Data parsing does not establish commissioned TPS integration or intended clinical use | No patient data without proper rights |
| F-06 | Translate biological states into *real patient* target/OAR objectives, dose, fractionation or therapy changes | **NOT IMPLEMENTED** | Potential patient-specific treatment-planning device function, requires expert regulatory and clinical risk review | Hard STOP until authorized |
| F-07 | Exchange or alter plan data with a production commissioned TPS | **NOT IMPLEMENTED** | Significant interoperability and device safety implications; FDA and institutional review needed | Hard STOP |
| F-08 | Connect to treatment delivery hardware or authorize a treatment | **OUT OF SCOPE; NEVER ALLOWED BY CURRENT PROTOTYPE** | Potential high consequence treatment-device control | Reject any feature/action granting authority |
| F-09 | Report outcomes or advise clinical decisions based on real patients | **NOT VALIDATED** | Human-subjects, patient safety, regulatory and model generalizability consequences | Institutional approval + external evidence |

## Mandatory commercial claim rules (all present claims are **research-stage**)

**May say, with exact evidence:** 'BAROS EvidenceGate is a research software prototype for pre-TPS evidence qualification'; 'synthetic tests demonstrate specific developer-authored decisions and rejection cases'; 'the current software does not compute clinically validated dose, control treatment, or authorize care'; 'external TPS/physics evaluation and market validation are not yet complete'.

**Must NOT say:** 'FDA-exempt', 'FDA-cleared', 'FDA-approved', 'clinical decision support non-device', 'patient safe', 'dose verified', 'treatment ready', 'works with RayStation/Ethos', 'optimizes radiation therapy', 'improves survival', 'prevents patient injury', '>55% safer', or any similar clinical or competitive claim without proper independent evidence and legal/regulatory approval. A nonprofit laboratory's informal willingness to read a paper is not regulatory approval.

**Not established:** Non-Device CDS applicability, FDA classification/product code, 510(k)/De Novo/PMA route, investigational study requirements, QMS implications, FDA software documentation/cybersecurity expectations, commercial product claims, export control, professional liability or IRB/human-subjects status. These require qualified counsel/regulatory professionals and appropriate FDA/IRB contacts.

## Independent safety and commercial reviews required before any clinical product claims

1. Freeze a written **target product profile**: exact customer, user, intended indication, real patient versus mock cases, role in the planning pathway, evidence types, decision timing and whether a clinician can *independently review the basis* of the recommendation. Do not insert clinical dose proposals into that profile without a documented new risk review.
2. Have device regulatory counsel or qualified quality/regulatory personnel perform a function-specific FDA policy analysis, with the current January 2026 CDS guidance and Digital Health Policy Navigator as sources. Document reasoning and unresolved questions rather than declaring an exemption.
3. Obtain an independent clinical physicist/radiation oncologist review of what the software's output actually could change in a clinical TPS workflow, including unsafe manual bypass and erroneous biological state. Institutional controls and measurement tolerances are theirs to define, not developer-selected.
4. Obtain a formally agreed partner technical study and appropriate approval before processing real person-related data. Confirm sponsor/IRB determinations, data use, informed consent or waiver if applicable, security, retention and limitation on clinical research. This register does not grant any of these approvals.
5. If development transitions toward a patient-specific medical function, pause clinical integration and re-evaluate device requirements with qualified regulatory advice, including whether FDA interaction through an appropriate pre-submission mechanism is indicated. Do not assume one mandatory route from this screen.
6. Once actual intended use and risk classification are determined, develop a suitable device quality/safety lifecycle. No internal test count substitutes for process and external evidence.

## Impact on NIH/NCI Phase I case

NCI program reviewers requested a **commercializable product**. The dossier must avoid a false choice between 'no clinical medical device because we call it research' and 'validated treatment product because synthetic tests pass'. A **research-only development stage may investigate a future regulated product**, with a credible regulatory and validation pathway and budget. Conversely, a nonclinical research quality tool has to demonstrate that a customer will buy it and that claims are honestly limited.

The proposed Stage A software study and Stage B partner-governed TPS/phantom feasibility are research milestones, not clinical delivery. The business application remains premature until an eligible applicant, product use, institution partnership, legal data rights, realistic study cost and regulatory plan are documented.

## Decision

**Status: OPEN / EXTERNAL EXPERT REVIEW REQUIRED.** No FDA classification or healthcare use authorization is claimed. Preserve independent ownership/IP review before publishing commercial details. Any FDA/partner contact, formal filing, expenditure or legal commitment requires authorized decision-making, and none is being initiated by this document.
