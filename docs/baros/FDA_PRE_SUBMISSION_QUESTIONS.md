# BAROS FDA Pre-Submission / Q-Submission Question Set

Status: DRAFT FOR REGULATORY COUNSEL / CLINICAL-PARTNER REVIEW

Purpose: obtain FDA feedback before any BAROS interventional clinical study or marketing-submission strategy is represented as settled.

This document does not assume the eventual classification, product code, submission type, IDE status, or whether every BAROS function will ultimately be regulated identically.

## 1. Device / intended-use summary to provide FDA

BAROS is a research-stage software framework intended to operate as an external radiotherapy optimization / decision-support layer interfacing with independently validated treatment-planning and dose-calculation systems. It does not replace independent final-dose recalculation, qualified medical-physics QA, or authorized physician review.

Before a Q-Submission, lock:

- exact indication and disease site;
- intended user(s) and use environment(s);
- treatment modality and delivery technique;
- supported TPS / machine interfaces;
- whether BAROS modifies plan parameters, proposes alternatives, or scores/ranks plans;
- degree of automation and time-criticality;
- biological models/parameters that can affect output;
- biological/anatomical measurements that can trigger adaptation;
- trigger and qualification thresholds;
- phase-coupling/temporal-state logic;
- hold-last-valid and standard-plan fallback behavior;
- human-review and override controls;
- interoperability/data-flow boundary;
- cybersecurity/network architecture;
- software of unknown provenance / off-the-shelf dependencies;
- locked software/version/configuration;
- change-control strategy.

## 2. Current FDA framework to design against

As of September 2026, the BAROS regulatory package should explicitly account for:

- Content of Premarket Submissions for Device Software Functions (final, June 2023);
- Off-The-Shelf Software Use in Medical Devices (final, August 2023);
- Clinical Decision Support Software (final, January 2026);
- Cybersecurity in Medical Devices: Quality Management System Considerations and Content of Premarket Submissions (final, February 2026);
- Quality Management System Regulation (QMSR), effective February 2, 2026 and incorporating ISO 13485:2016 by reference;
- Content of Human Factors Information in Medical Device Marketing Submissions (final, May 2026);
- Applying Human Factors and Usability Engineering to Medical Devices (final, August 2026);
- Design Considerations and Pre-market Submission Recommendations for Interoperable Medical Devices (final, September 2017);
- Requests for Feedback and Meetings for Medical Device Submissions: The Q-Submission Program (final, May 2025).

Where relevant, evaluate FDA-recognized interoperability standards, including the ANSI/AAMI/UL 2800-1 family, rather than treating DICOM parsing alone as a complete interoperability assurance case.

## 3. Regulatory-classification questions

Ask FDA:

1. Based on the locked intended use, output type, degree of automation, time-criticality and human ability to independently review the basis of the output, which BAROS functions are device software functions and which, if any, might meet current non-device CDS criteria?
2. What device classification/product code and review pathway does FDA consider most appropriate for the regulated function(s)?
3. Does FDA consider the proposed clinical investigation significant risk under 21 CFR 812?
4. Would an IDE be required before the proposed interventional study?
5. Does FDA recommend a Pre-Submission before an IDE or marketing submission, and are there specific radiological-health review considerations for this radiotherapy optimization function?
6. Are there predicate devices or prior submissions FDA recommends evaluating before selecting 510(k), De Novo, PMA, or another route?
7. Does FDA recommend regulating the initial indication/configuration as a deliberately narrow single-site/single-TPS intended use before broader interoperability claims?

## 4. Software, model and evidence-governance questions

Provide requirements, architecture, traceability, expert-readout schema, verification results, dependency inventory, evidence-envelope schema, evidence-dependency graph, authorization model and exact build/evidence identities.

Ask:

1. Is the proposed software documentation level adequate for the intended risk and software function?
2. What independent verification does FDA expect for biologically informed objective functions that may change optimization behavior?
3. What evidence is expected for selection, calibration, uncertainty and applicability of TCP/NTCP/radiosensitivity/hypoxia/proliferation or related model terms?
4. Is explicit local-identifiability analysis an appropriate component of model assurance, and what additional evidence should accompany it?
5. How should low-observability/high-control model states and out-of-distribution inputs be represented and governed?
6. What evidence should demonstrate that BAROS correctly distinguishes a change that should trigger review from a measured state that is too uncertain or poorly identified to support adaptation?
7. What validation should be required for trigger sensitivity/specificity, false adaptation, missed adaptation, correct refusal, incorrect refusal, and degraded-mode fallback behavior?
8. Is the proposed phase-coupled temporal-control structure an appropriate way to prevent each fraction/adaptation phase from being optimized independently of neighboring phases, and what evidence would FDA expect for the chosen temporal model and weights?
9. Is dependency-aware claim invalidation an appropriate change-control mechanism when a calibration, model, TPS version or source artifact changes?
10. How should partner-controlled raw evidence, uncertainty, deviations, contradictions and reviewer identity be represented in a premarket evidence package?
11. If future versions introduce learned/AI components, what additional total-product-lifecycle evidence and change-control documentation would FDA expect?
12. What software-change categories should trigger partial versus full revalidation of the locked intended use?

## 5. Interoperability and nonclinical evidence questions

Provide:

- DICOM/TPS semantic and geometry validation;
- real-system interoperability test plan;
- measured-dose commissioning plan;
- anthropomorphic end-to-end plan;
- independent dose calculation;
- robustness and failure injection;
- human factors/use-related risk analysis;
- cybersecurity threat modeling and controls;
- external medical-physics review plan.

Ask:

1. Are the proposed measured-dose commissioning tests adequate for the intended radiotherapy techniques?
2. What additional nonclinical testing would FDA expect before an IDE or interventional study?
3. Does FDA expect multi-vendor or multi-platform verification before the initial clinical study, or can the first study be limited to one locked TPS/machine configuration?
4. What interface requirements, data-integrity checks, timing behavior, alarm/failure semantics and labeling should be specified for BAROS/TPS interoperability?
5. What evidence is expected for independent final-dose recalculation and for preventing a BAROS surrogate or stale dose from being treated as authoritative?
6. What level of fault injection is expected for malformed DICOM, coordinate mismatch, missing structures, unsupported plans, network interruption, stale data, version mismatch and partial workflow failure?
7. Are ANSI/AAMI/UL 2800-1 family concepts appropriate for the planned interoperability assurance case?

## 6. Human factors / usability questions

BAROS is designed for expert clinical users, but expert users can still make use errors under workload and time pressure. Provide a task analysis covering at minimum:

- accepting/rejecting a BAROS proposal;
- understanding why an adaptation trigger fired;
- understanding why a triggered state was refused;
- recognizing HOLD_LAST_VALID versus FALLBACK_STANDARD behavior;
- inspecting model assumptions and confidence/limitations;
- recognizing unsupported/out-of-distribution cases;
- detecting stale/mismatched patient or plan context;
- interpreting hard-constraint failures;
- resolving BAROS-versus-TPS disagreement;
- reverting to standard workflow;
- reviewing provenance/version information;
- responding to cybersecurity or data-integrity alerts.

Ask FDA:

1. Which tasks should be treated as critical tasks for formative and summative human-factors validation?
2. What information must be visible in the clinical user interface so a qualified user can understand the basis and limitations of a BAROS output?
3. What use-error scenarios should be included in simulated-use testing?
4. What evidence is required to show that fail-closed behavior does not itself introduce unsafe delay, confusion, or workarounds?

## 7. Cybersecurity / quality-system questions

Ask FDA whether the proposed lifecycle controls are adequate, including:

- QMSR / ISO 13485:2016 alignment;
- design/development records;
- risk management and hazard traceability;
- SOUP / OTS dependency controls and vulnerability monitoring;
- secure update and rollback;
- authentication/authorization;
- audit logging and evidence integrity;
- configuration management;
- defect/CAPA process;
- complaint/adverse-event handling;
- postmarket monitoring;
- revalidation triggers.

For a network-capable deployment, explicitly ask what cybersecurity documentation FDA expects under the February 2026 final guidance and, if BAROS becomes a cyber device, what section 524B obligations apply.

## 8. Clinical-study design questions

Provide the staged retrospective, prospective-shadow and interventional protocols.

Ask:

1. Is the proposed first intended-use population appropriately narrow?
2. Are the proposed primary safety and effectiveness endpoints clinically meaningful for the intended use?
3. Is the standard-of-care comparator appropriate?
4. Is superiority, non-inferiority or another design most appropriate for the eventual effectiveness question?
5. Are the proposed safety stopping rules adequate?
6. Does FDA recommend independent endpoint adjudication or a Data Safety Monitoring Board for the expected risk?
7. What follow-up is necessary for toxicity or outcome endpoints?
8. What evidence would support the closed-loop BAROS operating claim specifically: longitudinal measurement, trigger, qualification, re-optimization proposal, independent recalculation/validation, and fallback?
9. Should controller-performance endpoints (false adaptation, missed adaptation, correct/incorrect refusal, fallback frequency) be treated as separate safety/performance endpoints from plan-quality endpoints?
10. What evidence is needed to generalize from the initial site/configuration to additional institutions, TPS versions or delivery platforms?

## 9. 98.7% internal evidence-target question

BAROS has an internal high-confidence validation target. It is not an FDA-established threshold.

Ask FDA whether the proposed statistical framing is useful or misleading for:

- absence of protocol-defined BAROS-attributable serious safety failure;
- complete-case dose-accuracy success;
- successful treatment-process use;
- a separate indication-specific clinical-effectiveness criterion.

Do not combine these into a single average. Do not describe 98.7% as a cure, survival or FDA acceptance probability.

## 10. Package requested before Q-Submission

- locked intended-use manifest;
- software/system architecture and data-flow diagram;
- expert technical readout and requirements traceability matrix;
- model registry, parameter provenance and identifiability/uncertainty report;
- risk analysis and hazard-control traceability;
- evidence-envelope and dependency-graph examples;
- DICOM/TPS interoperability specification;
- commissioning/end-to-end protocol;
- cybersecurity summary and dependency inventory;
- human-factors task/use-error analysis;
- retrospective/shadow-study protocol synopsis;
- statistical analysis synopsis;
- clinical-collaboration/site-intent letter if available;
- known limitations and unresolved hazards.

## 11. Claim-control rule

Until FDA feedback and required external evidence are obtained, BAROS may not state that:

- FDA agrees with the internal 98.7% target;
- BAROS is cleared/approved/authorized;
- clinical-study risk classification is settled;
- the intended regulatory pathway is settled;
- a detailed readout or internal governance gate is equivalent to validation;
- BAROS is safe/effective for patient care.
