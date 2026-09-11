# ECHO SENTINEL LINK provider-retrieval pilot v1.9

## Purpose

This record advances the v1.8 external-anchor program by exercising a real authorized remote-provider publication and retrieval path with a deliberately non-sensitive synthetic transport object before any production ECHO checkpoint is published.

It does **not** replace or weaken `ECHO_CHECKPOINT_V1_8_EXTERNAL_ANCHOR_DESIGN.md`. The v1.8 verifier remains authoritative for deterministic checkpoint-anchor requests, evidence artifacts, receipts, and `READ_BACK_CONTENT_MATCH`.

## Pilot object

Provider: GitHub repository content service.

Repository: `Bdavis1390/Sara_pro`.

Published object:

`external_anchor_pilots/github/2026-09-11/provider-retrieval-pilot-v1.json`

Publication commit:

`6e87e711b82d6e7349af09b8ef05002d42a04556`

GitHub provider blob SHA:

`89c9a74c3fe53cb0ee38cd49c9901c4079b34203`

Local byte-content SHA-256 before publication:

`cecd3c4f029d4d90971d8e99b99c32f722286d957f734159e7662ab9bca0b003`

Canonical pilot-payload SHA-256:

`12ae1597e4443132c83222ab3d54efd88c6bb6eda7910a9a3b2d154eb755a1f1`

## Retrieval evidence

The published object was subsequently retrieved through two provider surfaces:

1. the GitHub Contents API on branch `echo-provider-retrieval-pilot-v1-9`; and
2. a raw GitHub URL pinned to publication commit `6e87e711b82d6e7349af09b8ef05002d42a04556`.

Both returned the published JSON content. The Contents API reported provider blob SHA `89c9a74c3fe53cb0ee38cd49c9901c4079b34203`.

The bounded evidence record is stored at:

`external_anchor_pilots/github/2026-09-11/provider-retrieval-evidence-v1.json`

Its canonical evidence digest is:

`ef15b0149cf6d3b25535a6cdd4ffe430fcd3301db483fef7a3e82c4e31a77770`

## Bounded result

`PROVEN INTERNALLY — a non-sensitive synthetic Worldshepherd provider-path pilot object was published to GitHub and retrieved through both the GitHub Contents API and a commit-pinned raw GitHub path with matching content.`

This result proves only the remote provider transport/retrieval substrate used by the pilot.

The pilot object is explicitly **not** a `WS-ECHO-CHECKPOINT-ANCHOR-REQUEST-V1` object. Therefore this result does **not** establish that a signed ECHO checkpoint has been externally anchored.

## Claims boundary

This pilot does not establish:

- independent third-party attestation;
- immutable or WORM retention;
- trusted timestamp or transparency-log guarantees;
- privileged rollback resistance;
- legal chain-of-custody status;
- production HSM/KMS custody;
- exactly-once transport;
- certification or government authorization;
- customer acceptance; or
- physical-system qualification.

GitHub is an external service, but the repository/account is under Worldshepherd user control. Provider retrieval is therefore evidence of remote observability and content retrieval, not independent attestation.

## Relationship to v1.8

The next gate is intentionally stricter than this pilot:

1. generate a real `WS-ECHO-CHECKPOINT-ANCHOR-REQUEST-V1` from a verified signed ECHO checkpoint using the v1.8 implementation;
2. publish that exact deterministic request through an authorized remote provider path;
3. retrieve it through a separately evidenced provider read path;
4. retain provider locator, provider response metadata, retrieved document, evidence artifact, and receipt;
5. require the v1.8 verifier to return `READ_BACK_CONTENT_MATCH` on the retrieved provider document; and
6. preserve the provider-retrieval evidence separately so local content verification cannot grant itself remote provenance.

Only after that sequence may Worldshepherd make the bounded v1.8 statement that the identified checkpoint anchor request was observed through the separately evidenced provider retrieval and its content matched the local deterministic anchor request.

Even then, independent attestation, WORM/immutability, trusted timestamping, privileged rollback resistance, HSM/KMS custody, exactly-once transport, certification, and physical qualification remain separate gates.
