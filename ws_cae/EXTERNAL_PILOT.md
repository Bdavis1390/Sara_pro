# WS-CAE External Chain Patch Pilot

The next validation milestone is an implementation or review independent of the WS-CAE authors.

## Chain-side pilot

A participating chain team can:

1. copy `examples/chain.patch.template.json`;
2. populate it using only primary public evidence;
3. run `python -m ws_cae.patch_cli <patch> --pretty` or the reusable chain-patch action;
4. publish the resulting patch or a documented semantic disagreement.

A successful pilot does **not** require the chain to be post-quantum ready. A truthful low-maturity or classical state is valid evidence.

## Relying-party pilot

A custodian, wallet, exchange, auditor, insurer, treasury, or risk engine can:

1. define an independent consumer policy;
2. evaluate one or more published chain patches;
3. document whether WS-CAE reduced repeated bespoke diligence;
4. preserve any semantic disagreement rather than changing the chain's facts.

## Acceptance criteria

The pilot counts as independent reproduction only if the external participant independently consumes the published format and either:

- reaches materially the same authority/maturity/commitment classification; or
- publishes a concrete disagreement identifying the field or semantic rule that failed.

The strongest next milestone is two-chain reproduction by an independent relying party, preferably covering two different architectural families.

## Claims boundary

Participation is not endorsement, certification, standards adoption, or a security approval. External evidence must be attributable to the external participant before WS-CAE can claim independent reproduction.

The current package has no explicit reuse license. Issue #220 remains a legal/IP blocker for copying or redistribution beyond whatever rights independently apply.
