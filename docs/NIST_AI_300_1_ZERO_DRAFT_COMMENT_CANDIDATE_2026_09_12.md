# Worldshepherd comment candidate — NIST AI 300-1 ipd

**Status:** PREPARED_NOT_SUBMITTED  
**External-action gate:** Human review and explicit submission authorization required.  
**Public-comment deadline referenced by NIST:** September 16, 2026.  
**Proprietary content:** None intended. Review before release.  
**AI-assistance disclosure:** An AI assistant was used to help organize and draft this candidate. The submitter must independently review the content for accuracy, relevance, and real-world grounding before any submission.

## Source under review

NIST AI 300-1 ipd, *Guidance and Templates for Public-Facing AI Documentation: An AI Standards “Zero Draft” — Initial Public Draft*, July 2026, DOI: 10.6028/NIST.AI.300-1.ipd.

NIST states that the current draft covers public-facing documentation of AI datasets and models and does not address documentation of entire AI systems. The candidate comments below do **not** propose silently redefining an AI model to mean an entire system. Instead, they propose narrowly scoped bridges that preserve the model/dataset focus while reducing ambiguity when a documented model is deployed inside a larger system.

## Comment 1 — Add a bounded system-context bridge without expanding the model definition

### Concern

A model-only artifact can be technically correct yet materially misleading about deployed behavior when the model is surrounded by guardrails, retrieval components, tool connectors, orchestration logic, post-processing, external services, or human-approval controls. This is especially important for agentic systems, where side effects and operational behavior may be determined outside the model object.

### Suggested change

Add an optional **System Context** field or profile extension to the model documentation template. It should permit a provider to identify, at a high level:

- whether the documented model is normally used alone or as one component of a larger AI system;
- material surrounding component classes, such as retrieval, guardrails, post-processing, tool-use/orchestration, external services, and human oversight;
- which reported characteristics apply to the model object versus the integrated system;
- a reference to separate system-level documentation when such documentation exists; and
- explicit `not_applicable`, `not_available`, or `not_publicly_disclosed` states rather than forcing unsupported detail.

This bridge would preserve the draft’s model/dataset scope while reducing the risk that model-level documentation is interpreted as a system-level assurance claim.

## Comment 2 — Make supersession and freshness machine-visible

### Concern

The draft already includes model/documentation identity and version information and appropriately emphasizes freshness and maintainability. A remaining interoperability need is to make the relationship among current, superseded, deprecated, and withdrawn artifacts independently checkable.

### Suggested change

Using the draft’s existing identity/version fields, consider adding or clarifying fields for:

- publication and last-reviewed timestamps;
- supersedes / superseded-by relationships;
- withdrawn, deprecated, or revoked status when applicable;
- material change categories that trigger documentation review; and
- optional content digest or other integrity reference for machine-readable artifacts.

The objective is not to prescribe a particular registry technology or duplicate existing identity/version fields. It is to make supersession and freshness independently checkable.

## Comment 3 — Distinguish claims from their supporting evidence and evidence scope

### Concern

Public documentation can combine a performance statement, evaluation description, and broad conclusion into one narrative. When that occurs, a bounded result can be read more broadly than its evidence supports.

### Suggested change

For reported performance, safety, reliability, robustness, or other evaluated characteristics of the documented dataset/model, consider fields that distinguish:

1. **Claim or finding** — what is being asserted;
2. **Evidence reference** — test/report/dataset identifier or public citation;
3. **Evaluation scope** — model version, dataset, environment, task, sample size, and relevant conditions;
4. **Evaluator relationship** — provider-internal, customer/partner, or independent third party, where appropriate;
5. **Evidence date/freshness**;
6. **Known limitations and unresolved contradictions**; and
7. **Applicability boundary** — what the evidence does *not* establish.

Separate integrated-system or deployment evidence should remain outside the model-profile evidence fields and, when relevant, be referenced through System Context or separate documentation. This structure would improve later comparison and evaluation without requiring NIST to prescribe specific evaluation methods.

## Comment 4 — Preserve negative, null, failed, and contradictory evaluation evidence when material

### Concern

Documentation processes can unintentionally favor successful or canonical evaluations, causing failed tests, null results, contradictory replications, or known limitations to disappear from the public artifact even when they materially affect suitability.

### Suggested change

Within evaluation/performance documentation, recommend that providers disclose material negative, null, failed, or contradictory evidence when omission would change a reasonable consumer’s interpretation of model suitability. Where details cannot be public for privacy, proprietary, legal, or other documented reasons, allow a bounded disclosure that such evidence exists together with the reason for withholding detail.

This is consistent with artifact correctness and informativeness while still respecting judiciousness.

## Comment 5 — Use the existing field identifiers for interoperable machine-readable documentation

### Concern

Human-readable PDFs and web pages are valuable, but automated comparison and reuse become fragile when field semantics, value types, null states, and profile-version behavior are not represented in a reference serialization.

### Suggested change

Using the draft’s existing stable numeric field identifiers, consider publishing a normative or reference machine-readable schema/serialization for the default dataset/model profiles. Providers could still render the same information as HTML, PDF, or other media.

Useful schema properties would include:

- data type and cardinality;
- enumerated status values where appropriate;
- explicit unknown/not-applicable/not-disclosed representations;
- profile/version identifier; and
- extension rules that preserve forward compatibility.

The goal is semantic interoperability, not a requirement for one storage format and not a request to add a second identifier scheme.

## Comment 6 — Clarify model-level assurance language and references to wider evidence

### Concern

A reader may interpret a model card statement such as “safe,” “secure,” “robust,” or “validated” as applying to a deployed system even when the evidence applies only to a bounded dataset/model evaluation.

### Suggested change

Add guidance that assurance-relevant statements in the model profile identify whether the evidence concerns the documented dataset or model object and state the applicable evidence class and boundary. If broader integrated-system, deployment, or external-assessment evidence is relevant, reference it through the optional System Context bridge or separate documentation rather than representing it as model-profile evaluation evidence.

Where the template remains model-only, broader operational conclusions should be clearly marked as outside the artifact’s evidentiary scope unless separately supported.

## Comment 7 — Treat redaction/withholding as a documented state rather than silent absence

### Concern

The draft appropriately recognizes privacy, proprietary information, malicious-use risk, and legal obligations. Silent omission, however, prevents consumers from distinguishing “not considered” from “considered but intentionally withheld.”

### Suggested change

For fields where disclosure is optional or may be inappropriate, support explicit states such as:

- `not_available`;
- `not_applicable`;
- `not_publicly_disclosed`;
- `withheld_privacy`;
- `withheld_proprietary_or_legal`;
- `withheld_other_documented_reason`.

A short rationale should be encouraged when appropriate. This preserves judiciousness without converting absence into apparent completeness.

## Proposed future-work note — agentic AI system documentation

Because the present draft deliberately leaves full AI-system documentation to future work, NIST/INCITS/SC 42 should consider a future profile or companion standard for agentic AI systems. Candidate system-level fields include component/version graph, tool/action permissions, external side-effect boundaries, human-approval points, identity separation, event/decision provenance, replay/recovery behavior, and deployment-state changes.

This is proposed as **future work**, not as a request to expand every model-documentation artifact into a complete system dossier.

## Claims boundary

This document is a Worldshepherd review candidate based on internal software-governance experience and public NIST material. It does not claim NIST participation, acceptance, endorsement, standards conformity, independent validation, or external adoption. It is not legal advice and should contain only material approved for public release.
