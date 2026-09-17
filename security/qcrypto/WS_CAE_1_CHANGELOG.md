# WS-CAE-1 Changelog

## v0.1 — 2026-09-13

Initial Worldshepherd draft.

Introduced:

- stable authority identity separated from authentication;
- versioned authenticator sets;
- versioned authorization policy;
- pre-positioned recovery semantics;
- chain/domain/replay binding requirements;
- evidence binding;
- algorithm-family diversity for high-value profiles;
- chain-adapter abstraction;
- CAE-C0 through CAE-C5 conformance language;
- mandatory separation between account/vault authorization claims and consensus/validator claims;
- initial public evidence mapping for Algorand, Sui, and Ethereum;
- independent-review request and review log.

Known gaps:

- no independent external implementation yet;
- no external certification;
- no standards-body adoption;
- no completed independent review;
- machine conformance classifier was not added after a platform safety block;
- adapter registry draft was not added after a platform safety block.

Next target: independent review plus at least one external or separately implemented profile parser/checker that can reproduce the same conformance interpretation from the published specification and evidence bundle.
