# NIST AI 300-1 ipd — Worldshepherd comment clause crosswalk

**Status:** SUPPORTING REVIEW MATERIAL / NOT SUBMITTED  
**Purpose:** Tie the prepared Worldshepherd comment candidate to exact draft clauses and avoid broad comments that the source does not support.  
**AI-assistance disclosure:** An AI assistant was used to help analyze and organize this crosswalk. Human review is required before any external use.

## Source anchors

NIST AI 300-1 ipd, July 2026, DOI `10.6028/NIST.AI.300-1.ipd`.

The draft states that:

- it covers public-facing documentation of AI datasets and AI models;
- it does **not** address documentation of entire AI systems, leaving that to future work because system-level documentation practices are less mature;
- an AI model is scoped to model architecture and parameters, excluding related system components such as post-processing modules;
- NIST explicitly asks reviewers how model documentation could encompass additional components without requiring documentation of entire systems;
- NIST will consider input received by September 16, 2026;
- submissions become part of the public record; and
- if AI assistants are used for feedback, the use should be disclosed and the submitter should ensure real-world insights are accurately and concisely captured.

## Crosswalk

| Candidate comment | Exact draft anchor | Source-supported observation | Recommended precision |
|---|---|---|---|
| Bounded system-context bridge | Scope, lines 109–122; Definitions, lines 161–164; reviewer note following line 164 | The draft deliberately excludes complete AI-system documentation but expressly solicits input on whether additional served/shipped components should be represented without expanding to the whole system. | Do **not** redefine `AI model`. Add a narrowly scoped optional subfield/profile extension that identifies material surrounding component classes and states that they are outside the documented model object's evidentiary scope. |
| Version / supersession / freshness | Model template Root Field 1; Default Model Profile field 1.12; Root Field 7 Maintenance and Monitoring | The draft already requires enough identifying information to determine whether a given model is the documented model and includes a documentation-version identifier; maintenance guidance covers updates/versioning/retirement. | Narrow the request to explicit supersession/deprecation links, last-reviewed timestamp, and optional artifact integrity reference rather than implying identity or version fields are absent. |
| Claim/evidence scope | Model template Root Field 6 Evaluation; Intended Use Root Field 2 | Evaluation may include protocols, datasets, risk analyses, quantitative results, and qualitative analysis. | Recommend structured subfields for the evaluated dataset/model object, evidence reference, evaluation conditions, evaluator relationship, limitations, and applicability boundary. Separately documented system or deployment evidence should only be referenced through the optional System Context bridge, not promoted into Root Field 6 as model-profile evidence. |
| Negative / contradictory evidence | Root Field 6 Evaluation; artifact correctness/informativeness/judiciousness guidance | Evaluation evidence is intended to help interested parties assess quality, fitness, and risks, while the artifact guidance balances informativeness with judiciousness. | Recommend disclosure of *material* negative/null/contradictory findings where omission would materially change suitability interpretation, with bounded withholding states where details cannot be public. |
| Machine-readable semantic interoperability | Scope permits digital artifacts; field/subfield/root-field definitions; artifact interoperability guidance; profile mechanism | The draft already uses stable numeric field identifiers and profiles and recognizes digital forms such as JSON. | Ask for a normative or reference machine-readable schema/serialization that uses the existing field identifiers and defines types/cardinality, explicit null/not-applicable states, profile versioning, and extension semantics. Do not require a single storage technology. |
| Model vs system assurance language | Scope/system exclusion; AI-model definition; Root Field 6 Evaluation | A model evaluation can be correct while not establishing system-level operational behavior. | Recommend that Root Field 6 identify whether the evidence concerns the documented dataset or model object. System-level tests, deployment observations, or broader assurance evidence should remain outside the model profile and, when relevant, be referenced through System Context or separate documentation. |
| Explicit withholding state | Artifact judiciousness; privacy preservation; proprietary-information protection; legal obligations; optional/recommended field designations | The draft recognizes reasons not to disclose some details. | Add status values that distinguish `not_applicable`, `not_available`, and `not_publicly_disclosed` plus bounded reason categories, rather than treating all blank/omitted fields equivalently. |
| Future agentic-system documentation | Scope note leaving system documentation to future work; Zero Draft project page lists future concepts/architectures as possible future scopes | The current document intentionally does not standardize full AI-system documentation. | Keep agentic-system component graphs, tool/action permissions, external side effects, authorization boundaries, provenance, replay/recovery, and deployment-state transitions in a **future-work** recommendation, not in the present model definition. |

## Proposed replacement/additional text for the model/system boundary reviewer question

The following text is deliberately phrased as an optional addition to the model profile rather than a redefinition of `AI model`:

> **System Context (Optional):** High-level information identifying whether the documented model is commonly deployed as one component of a larger AI system and, when useful for interpreting model-level documentation, the classes of surrounding components that materially affect how model inputs or outputs are produced, constrained, transformed, or acted upon. Examples may include retrieval components, guardrails, post-processing, orchestration/tool-use components, external services, and human oversight. This field should distinguish characteristics and evaluation evidence of the documented model object from characteristics or evidence of the larger system and may reference separate system-level documentation where available. Inclusion of this field does not expand the definition of the documented AI model to encompass those surrounding components.

### Why this wording is narrower than full system documentation

It does not require:

- a complete architecture diagram;
- enumeration of every service or dependency;
- disclosure of proprietary implementation details;
- system-level conformance claims; or
- performance claims about components that have not been separately evaluated.

It only supplies enough context to prevent a model-level artifact from being read as if it described the whole deployed system.

## Proposed subfields for Evaluation (Root Field 6)

If NIST/INCITS prefers profile specialization rather than a new root field, the following subfields could improve evidence scope without prescribing TEVV methodology:

- `6.x Evaluation Subject` — documented dataset or model object;
- `6.x Evidence Reference` — report/test/dataset/public citation identifier;
- `6.x Evaluation Conditions` — version, task, environment, sample size, and material configuration;
- `6.x Evaluator Relationship` — provider-internal, customer/partner, or independent third party, when relevant;
- `6.x Material Limitations or Contradictions` — known results that constrain interpretation;
- `6.x Applicability Boundary` — explicit statement of what the evidence does not establish.

Where separate integrated-system or deployment evidence materially affects interpretation of the model documentation, the model profile should reference that evidence only through the optional System Context field or separate system-level documentation. These fields therefore improve the scope of model/dataset evidence without silently expanding Root Field 6 into whole-system documentation.

## Submission hygiene

Before any submission:

1. remove any statement that cannot be traced to the draft or genuine Worldshepherd implementation experience;
2. preserve the AI-assistance disclosure;
3. keep the response non-proprietary because NIST states submissions become part of the public record;
4. avoid claims of NIST participation, endorsement, conformity, or acceptance; and
5. have CRE1AWS explicitly authorize the external submission.
