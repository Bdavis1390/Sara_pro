# WS-CAE Governance and Change Control

Status: research governance for the `0.x` series; not a standards-body process.

## Objectives

WS-CAE governance is intended to keep the authority profile vendor-neutral, chain-neutral, falsifiable, and compatible with independent implementations.

The profile must not become a mechanism for Worldshepherd, a particular blockchain, a custody provider, or a cryptographic vendor to redefine security claims in its own favor.

## Public change process

Material changes should be proposed publicly through repository issues or pull requests and should include:

- the problem being addressed;
- affected fields or semantics;
- compatibility impact;
- examples from at least two materially different account models when the change is cross-chain;
- claims-control impact;
- known disagreements or alternative approaches.

Significant semantic changes should not be introduced only through implementation code without corresponding documentation and tests.

## Compatibility rule

A field meaning must not be silently broadened or narrowed.

If an existing profile could produce a materially different interpretation after a change, the change requires a version transition and migration note.

Unknown fields continue to fail closed in the reference implementation.

## Evidence and disagreement

WS-CAE should preserve disagreement rather than normalize it away.

An independent reviewer may dispute a maturity state, authority classification, or evidence claim. The disagreement should remain inspectable and should not be treated as a failed contribution merely because it conflicts with the current reference profile.

## Chain neutrality

Changes must not require one chain's account model to become the canonical model for every other chain.

Native rekey, account abstraction, alias-based identity, programmable vaults, UTXO-based mechanisms, and future authority architectures may require different adapters while retaining common profile semantics where genuinely comparable.

If a mechanism cannot be represented without distortion, the correct response is to extend or narrow the profile, not force the chain into an inaccurate category.

## Algorithm neutrality

WS-CAE does not designate a preferred PQ signature family or consensus mechanism.

Algorithm-specific requirements belong in relying-party policy or chain-specific evidence unless a future version explicitly standardizes additional semantics after review.

## Consumer independence

Chain profiles describe asserted facts. Consumer policies describe requirements.

A chain maintainer must not need to modify the chain profile because one custodian or wallet changes risk appetite. Likewise, a consumer must not need permission from the chain to apply a stricter policy.

## Stewardship during 0.x

Worldshepherd currently acts as research steward for the reference repository. That role does not constitute standards authority.

During the `0.x` research series, the steward may accept or reject changes, but material decisions should include a public rationale and preserve dissenting evidence where relevant.

## Promotion toward 1.0

A future `1.0` candidate should not be declared solely by the original authoring process. At minimum it should require:

- independent reproduction across multiple ecosystems;
- external technical review;
- a stable compatibility policy;
- an explicit license suitable for the intended adoption model;
- published change-control and deprecation rules;
- documented handling of disputes and evidence corrections;
- evidence that at least one relying party has consumed profiles independently of the reference implementation.

## Anti-capture rule

No chain, vendor, custodian, standards participant, or Worldshepherd itself should receive a conformance advantage solely because it controls the reference implementation.

Conformance should remain reproducible from published semantics and evidence.

## Claims boundary

This governance document does not transform WS-CAE into an accredited standard, consortium specification, regulatory framework, or certification program.
