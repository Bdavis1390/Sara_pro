# WS-CAE Compatibility and Versioning

Current research version: `0.1.0-research`

WS-CAE is not yet a standards-body specification. This policy exists so external reviewers and adopters can pin behavior while the research profile evolves.

## Compatibility rules

The `0.x` research series may add fields or refine semantics, but the reference CLI fails closed on unknown fields so silent reinterpretation is avoided.

For a given pinned commit:

- profile vocabulary is fixed by `ws_cae_profile.schema.json`;
- consumer-policy vocabulary is fixed by `ws_cae_policy.schema.json`;
- CLI behavior is fixed by `ws_cae_cli.py` and its regression tests;
- the composite action is fixed by `.github/actions/ws-cae-conformance/action.yml`.

External users should pin an immutable commit SHA. Moving branches are suitable for review but not for reproducible production gating.

## Version-change expectations

Patch-level research updates should preserve existing field meanings and only fix implementation/documentation defects.

Minor research updates may add optional fields, new adapter classes, or additional policy capabilities. Existing meanings should not be silently broadened.

A future `1.0` candidate would require, at minimum:

- independent reproduction across multiple ecosystems;
- published change-control rules;
- stable field semantics;
- a migration path from the latest research version;
- explicit handling of deprecated vocabulary;
- external review of the claims and evidence model.

## No lock-in guarantee

The JSON profile semantics are intended to be implementable independently of this repository. Consumers may reimplement the checks or translate equivalent evidence into another system.

WS-CAE should be treated as an interoperability profile, not as a requirement to run Worldshepherd software.

## Security and claims boundary

A version number indicates interface stability only. It does not imply certification, standards-body approval, production security review, regulatory compliance, or post-quantum security of an underlying chain.
