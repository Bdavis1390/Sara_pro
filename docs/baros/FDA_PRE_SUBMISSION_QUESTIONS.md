# BAROS FDA Pre-Submission / Q-Submission Question Set

Status: DRAFT FOR REGULATORY COUNSEL / CLINICAL-PARTNER REVIEW

Purpose: obtain FDA feedback before any BAROS interventional clinical study or marketing submission strategy is represented as settled.

This document does not assume the eventual classification, submission type, or IDE status.

## 1. Device / intended-use summary to provide FDA

BAROS is a research-stage software framework intended to operate as an external radiotherapy optimization / decision-support layer interfacing with validated treatment-planning and dose-calculation systems. It does not replace independent final-dose recalculation, qualified medical-physics QA, or authorized physician review.

Before submission, lock:

- exact indication and disease site;
- target user(s);
- treatment modality and delivery technique;
- supported TPS / machine interfaces;
- whether BAROS modifies plan parameters, recommends alternatives, or only scores/ranks plans;
- degree of automation;
- human-review controls;
- cybersecurity/network architecture;
- locked software/version/configuration.

## 2. Regulatory-classification questions

Ask FDA:

1. Based on the locked intended use and level of automation, what device classification/product code and review pathway does FDA consider most appropriate?
2. Does FDA consider the proposed clinical investigation significant risk under 21 CFR 812?
3. Would an IDE be required before the proposed interventional study?
4. Does FDA recommend a Pre-Submission before the IDE, and are there specific radiological-health review considerations for this software function?
5. Are there predicate devices or prior submissions FDA recommends evaluating before selecting 510(k), De Novo, PMA, or another route?

## 3. Nonclinical evidence questions

Provide the complete preclinical package and ask whether FDA considers the planned evidence adequate before human use:

- software requirements / traceability;
- architecture and hazard controls;
- verification/validation results;
- DICOM/TPS interoperability testing;
- measured-dose commissioning;
- anthropomorphic end-to-end testing;
- independent dose calculation;
- usability/human factors;
- cybersecurity;
- robustness/failure injection;
- change-control strategy;
- external medical-physics review.

Questions:

1. Are the proposed measured-dose commissioning tests adequate for the intended radiotherapy techniques?
2. What additional nonclinical testing would FDA expect before an IDE or interventional study?
3. Does FDA expect multi-vendor or multi-platform verification before the initial clinical study, or can the first study be limited to a single locked TPS/machine configuration?
4. What evidence is expected for biological-model components (TCP/NTCP/radiosensitivity/hypoxia or similar) if they influence optimization?
5. What level of independent verification is expected for software-generated constraints / plan modifications?

## 4. Clinical-study design questions

Provide the proposed retrospective, prospective-shadow, and interventional protocols.

Ask FDA:

1. Is the proposed first intended-use population appropriately narrow for an initial study?
2. Are the proposed primary safety and effectiveness endpoints clinically meaningful for BAROS's intended use?
3. Is the proposed comparator appropriate?
4. Is the proposed non-inferiority or superiority framework appropriate?
5. Are the proposed safety stopping rules adequate?
6. Does FDA recommend independent endpoint adjudication or a Data Safety Monitoring Board for the proposed risk level?
7. What follow-up period is necessary for any toxicity or clinical-outcome endpoint used to support effectiveness?
8. What evidence, if any, would FDA consider sufficient to support claims about adaptive optimization rather than only static planning?
9. What evidence is needed to generalize from the initial site/configuration to additional institutions, TPS versions, or delivery platforms?

## 5. 98.7% evidence-target question

BAROS has adopted an internal evidentiary target requiring independent support for >=98.7% probability of:

- absence of protocol-defined BAROS-attributable serious safety failure;
- full-case dose-accuracy success;
- successful treatment-process use;
- and a separate indication-specific clinical-effectiveness criterion.

Ask FDA whether this internal evidence framing is scientifically/regulatorily appropriate, and how FDA recommends expressing statistical uncertainty for each endpoint.

Do **not** present 98.7% as a regulatory threshold established by FDA. It is an internal BAROS validation target.

## 6. Quality-system / lifecycle questions

Ask FDA whether the proposed QMS package and lifecycle controls are adequate for the intended device function, including:

- QMSR / ISO 13485 alignment;
- risk management;
- design/development records;
- software lifecycle records;
- SOUP / OTS dependency controls;
- cybersecurity lifecycle;
- configuration management;
- defect / CAPA process;
- complaint / adverse-event handling;
- postmarket monitoring;
- software change-control and revalidation triggers.

## 7. Submission package requested from clinical partner before Q-Sub

- letter of clinical collaboration / study-site intent, if available;
- QMP review of dosimetry protocol;
- proposed investigator list;
- retrospective/shadow-study results if already complete;
- intended-use statement;
- risk analysis;
- clinical protocol synopsis;
- statistical analysis synopsis;
- device/software description;
- architecture and data-flow diagram;
- cybersecurity summary;
- preclinical evidence table;
- known limitations / unresolved hazards.

## 8. Claim-control rule

Until FDA feedback and the required external evidence are obtained, the repository may not state that:

- FDA agrees with the 98.7% target;
- BAROS is cleared/approved/authorized;
- the clinical-study risk classification is settled;
- the intended regulatory pathway is settled;
- BAROS is safe/effective for patient care.
