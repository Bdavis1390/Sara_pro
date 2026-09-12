# PRIME custody reconciliation — current-main staged port

**Status:** DRAFT / IMPLEMENTATION COMPLETE / VALIDATION PENDING / BLOCK MERGE  
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

## Stage B — conflict-aware current-main port completed

`prime_passport_api.py` had changed on current `main` after PR #149's merge-base, so the stale file was not copied wholesale. The remaining fixes were ported into the current event-outbox/provenance implementation:

1. malformed passport/authorization-registry durable state is classified as a server-side integrity failure rather than signer rejection;
2. stored authorization entries are structurally validated before new signer assertions are processed;
3. stored authorization windows longer than the signed 15-minute maximum are rejected as corrupt durable state;
4. successful activation of legacy READY records clears obsolete pre-ledger release authorization/target/key custody fields;
5. READY cleanup does not consume a nonexistent legacy authorization and removes false authorization attribution from successful activation provenance;
6. current-main API regressions cover corrupt passport state, corrupt top-level authorization registry, malformed authorization records, overlong stored windows, and legacy READY cleanup;
7. the existing QUARANTINED requalification flow remains separately gated and one-time consumable.

## Current incorporation gate

Implementation completion is not merge authorization. No merge or readiness promotion until:

- the complete exact-head workflow set is green on the final head;
- independent exact-head review reports no unresolved major defect;
- applicable stale PR #149 findings are dispositioned against the current-main implementation;
- issue #176 is updated with final evidence; and
- CRE1AWS explicitly authorizes incorporation.

## Claims boundary

Internal software-governance/custody evidence only. No external validation, partner/government acceptance, certification, physical capability, CMMC/NIST conformity, or operational authority is established by this branch.