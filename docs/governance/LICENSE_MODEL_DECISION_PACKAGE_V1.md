# Worldshepherd Licensing Model Decision Package v1

**Status:** `DECISION SUPPORT / NO LICENSE SELECTED`

## Why this matters now

`Bdavis1390/Sara_pro` is public but currently has no repository license establishing ordinary downstream reuse rights. That is now one of the clearest adoption and benchmark gaps.

Worldshepherd is also increasingly interacting with ecosystems whose repositories currently declare **Apache License 2.0**, including OCSF Schema, Open Policy Agent, Sigstore/Cosign, in-toto Witness, and GUAC. That does not force Worldshepherd to use Apache-2.0, but it makes an Apache-compatible contribution surface operationally simpler if upstream contribution is a goal.

This document does **not** select a license and is not legal advice.

## Decision principle

Do not license “Worldshepherd” as one undifferentiated body of material.

First separate the material into rights/maturity classes, then choose terms for each class. A license decision made for interoperability should not accidentally grant rights in unrelated patents, research data, partner material, biomedical work, physical designs, proprietary commercialization assets, trademarks, or material the rights holder does not control.

## Proposed material partition

### L1 — Open interoperability / assurance core candidate

Potential scope after ownership review:

- generic SARA evaluator tooling;
- evidence and custody schemas intended for public interoperability;
- standards bridges such as OPA, OCSF, OpenTelemetry, CycloneDX, SLSA/in-toto/Sigstore integration;
- generic fixtures and conformance tests intended for upstream reuse;
- non-domain-specific verification CLIs where publication is deliberate.

This is the strongest candidate for a permissive open-source surface because direct external reuse, forkability, test translation and upstream contribution are explicit objectives.

### L2 — Commercial integration / deployment layer candidate

Potential scope:

- customer-specific connectors;
- deployment hardening and managed-service components;
- proprietary integration automation;
- customer workflows, configuration and operational playbooks;
- commercial support/assurance packaging.

This material need not use the same outbound terms as L1.

### L3 — Scientific / physical / biomedical / domain R&D

Examples include BAROS, materials, RF/metasurfaces, propulsion, quantum, aerospace and other research lanes.

Default posture: **separate review required**. Research publication, source visibility, data sharing and patent strategy are different decisions from licensing a generic software-assurance core.

### L4 — Third-party / partner / externally constrained material

Any material carrying third-party rights, confidential terms, government/data-rights restrictions, export controls, jointly developed rights, partner restrictions or unclear provenance is excluded from any default repository-wide grant unless the authority to license it is documented.

### L5 — Brand / trademark / identity material

Worldshepherd names, logos and branding should be treated separately from software copyright licensing. An open-source software license should not be assumed to grant trademark rights.

## Candidate outbound models

### Option A — Narrow Apache-2.0 assurance/interoperability core + separately licensed commercial/domain layers

**Strategic advantages**

- strong compatibility with the presently verified OCSF, OPA, Cosign, Witness and GUAC ecosystems;
- explicit copyright and patent-license language appropriate to software collaboration;
- familiar to enterprise, standards and CNCF/OpenSSF-adjacent contributors;
- supports fork/test/upstream workflows without bespoke permission negotiation;
- can improve A15 licensing clarity and reduce friction for A16 upstream incorporation when applied to an intentionally bounded core.

**Risks / decisions requiring review**

- Apache-2.0 includes an express patent license from contributors for applicable patent claims; patent scope must be understood before use;
- repository history and ownership must support the grant;
- NOTICE obligations and third-party notices must be handled where applicable;
- material intended to remain proprietary must be excluded clearly rather than left ambiguous;
- contributor inbound terms must be compatible with the outbound model.

**Best fit if:** Worldshepherd wants a genuinely reusable assurance/interoperability core while retaining commercial/domain differentiation elsewhere.

### Option B — Dual license owned core: Apache-2.0 community path + commercial license for negotiated use/support

**Strategic advantages**

- keeps an open ecosystem path while permitting separate commercial terms for qualifying use cases;
- can support managed services, warranties, indemnity, support or additional proprietary modules under commercial terms.

**Complications**

- dual licensing only works cleanly if Worldshepherd retains sufficient copyright/relicensing authority over inbound contributions;
- contributor agreements or assignment strategy may become more important;
- the Apache-licensed version remains available under Apache terms, so the commercial value proposition must be something beyond simply “permission to use the same code.”

**Best fit if:** open ecosystem adoption and commercial integration are both explicit goals and contributor-rights governance is established early.

### Option C — Source-available or proprietary evaluation license

**Strategic advantages**

- maximum control over reuse, redistribution and commercialization;
- easier to reserve broad rights while IP review is incomplete.

**Strategic disadvantages**

- materially weaker upstream/open-source adoption path;
- likely incompatible with direct incorporation into Apache-licensed upstream projects unless specific contributions are separately licensed;
- evaluators and integrators must negotiate rights that competitors often grant by default;
- A15/A16 benchmark position remains weaker for open ecosystem use.

**Best fit if:** IP control and negotiated commercial access clearly outweigh upstream/open-source adoption.

## Recommended strategic direction — conditional, not authorized

If ownership/patent/third-party review confirms that Worldshepherd controls the relevant code, the strongest **interoperability and adoption** structure is likely:

> **A narrowly defined Apache-2.0 L1 assurance/interoperability core, with L2 commercial integration and L3 domain/scientific material explicitly outside that default grant unless separately reviewed.**

This is a recommendation for the rights holder to evaluate, **not a license selection** and not authorization to add Apache-2.0 to the repository.

The reason is architectural rather than cosmetic: standards bridges and conformance fixtures become more valuable when upstream projects can legally reuse them, while commercially differentiating customer/domain layers do not need to be surrendered merely to make the interoperability core usable.

## Required rights review before any license commit

For every file proposed for L1, answer and retain evidence for:

1. **Authorship / ownership** — who created the file and who owns copyright?
2. **Employment / contractor obligations** — was it created under an agreement that assigns or restricts rights?
3. **Third-party code/data** — does it include copied, generated, adapted or linked material with separate obligations?
4. **Patent impact** — could an outbound patent grant cover claims the rights holder intends to reserve or license differently?
5. **Partner/government restrictions** — is any material subject to data rights, NDA, export, CUI/classification, sponsor or procurement terms?
6. **AI-generated contributions** — what provenance/rights policy applies to generated code and what human review is retained?
7. **Documentation/data separation** — should docs, fixtures, schemas, examples, datasets and media use the same terms?
8. **Trademark boundary** — confirm software terms do not imply permission to use Worldshepherd branding.

Unresolved answer => **exclude from L1 pending review**. Do not guess.

## Inbound contribution model

Before accepting outside contributions to an open L1 surface, choose one documented inbound path, for example:

- Developer Certificate of Origin / signed-off-by process; or
- contributor license agreement if relicensing/dual-licensing strategy actually requires it.

Do not impose a CLA merely by habit; choose it only if the commercial/relicensing model needs those rights.

At minimum, `CONTRIBUTING.md` should state:

- contribution license expectations;
- DCO/CLA requirement if any;
- certification that contributors have the right to submit their work;
- security-reporting route;
- no confidential/CUI/classified/export-controlled/third-party proprietary submissions;
- review/acceptance does not create employment, partnership or compensation obligations.

## Repository implementation after rights-holder selection

Only after the decision and rights review:

1. add exact root license/reuse files;
2. document scope/exclusions prominently in `README.md`;
3. add `CONTRIBUTING.md` and inbound terms;
4. add `NOTICE` if applicable;
5. populate package metadata with correct SPDX identifier(s);
6. ensure generated SBOM/release/evaluator artifacts report the selected license only for covered material;
7. add automated checks preventing excluded material from silently entering the open core;
8. update #363 with the documented decision and evidence;
9. rerun OpenSSF Scorecard and Assurance Composite Benchmark A15/A16 evidence.

## Benchmark boundary

No A15 score promotion occurs from this decision package alone.

A15 can improve only when actual rights terms are selected and published for the evaluated artifact. A16 requires actual external use/incorporation, not merely compatible licensing.

## Decision record to complete

- Rights holder(s): `TO_BE_VERIFIED`
- L1 scope manifest: `TO_BE_CREATED`
- Selected outbound model: `UNDECIDED`
- Selected license(s): `UNDECIDED`
- Patent review: `OPEN`
- Third-party/provenance review: `OPEN`
- Inbound contribution model: `UNDECIDED`
- Legal review required/obtained: `TO_BE_DETERMINED`
- Authorization date: `NONE`

Until those fields are objectively closed, the repository remains **publicly inspectable but not generally licensed for downstream reuse**.
