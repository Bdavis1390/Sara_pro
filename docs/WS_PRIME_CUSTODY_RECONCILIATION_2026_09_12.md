# PRIME custody reconciliation — current-main staged port

**Status:** DRAFT / PARTIAL SAFE PORT / BLOCK MERGE  
**Issue:** #176  
**Source lineage:** stale draft PR #149, reconciled against current `main` rather than merged or rebased blindly.

## Stage A — safely ported

The following files were byte-identical on current `main` to PR #149's merge-base before this port, so the bounded fixes could be applied without overwriting newer mainline work:

- `worldshepherd_sara/prime_sentinel_authorization.py`
- `tests/test_prime_sentinel_authorization.py`

Ported behavior:

- prune expired VERIFIED/CONSUMED/SUPERSEDED records only after the signed replay window closes;
- retain malformed records so corruption remains visible/fail-closed;
- enforce a bounded 64-record live authorization window;
- reject true live-window capacity exhaustion;
- preserve authorization-ID and nonce replay protections;
- regressions for replay-window retention, live capacity exhaustion, and expired VERIFIED pruning.

## Stage B — not yet ported

`prime_passport_api.py` changed on current `main` after PR #149's merge-base. Its stale-branch file must **not** replace current mainline code wholesale.

The remaining conflict-aware work is:

1. classify malformed authorization-registry state as a server-side integrity failure rather than signer rejection;
2. validate stored authorization record structure and signed lifetime before processing new signer assertions;
3. clear obsolete pre-ledger READY authorization custody fields after a successful activation;
4. ensure successful READY cleanup provenance does not attribute authorization to a nonexistent legacy authorization;
5. preserve current-main event-outbox/provenance behavior and all newer custody semantics while adding the above fixes;
6. add current-main API regressions for each condition.

## Incorporation gate

No merge or readiness promotion until Stage B is complete, the full exact-head workflow set is green, independent exact-head review is clean, applicable review threads are dispositioned, and CRE1AWS explicitly authorizes incorporation.

## Claims boundary

Internal software-governance/custody evidence only. No external validation, partner/government acceptance, certification, physical capability, CMMC/NIST conformity, or operational authority is established by this branch.