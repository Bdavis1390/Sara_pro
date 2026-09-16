# OCSF #1724 Convergence Matrix

**Status:** issue-thread convergence / implementation aid. This is **not** merged OCSF specification text.

**Upstream issue:** https://github.com/ocsf/ocsf-schema/issues/1724

This file records what the public #1724 discussion has converged on strongly enough to guide a provisional conformance harness, while separating those points from still-open schema design.

## Strongly converged in the issue thread

- **Discovery category; new class rather than retrofit.** The discussion favors a dedicated agent trust-base inventory class rather than extending software/device inventory semantics.
- **Reuse `record_integrity`; do not invent class-specific chaining.** Every emission carries `metadata.uid`; genesis omits `prev_event`; later events link to the predecessor; `chain_uid` is scoped to `ai_agent.instance_uid`.
- **Declared and executed/observed state remain raw evidence.** Producers emit both sides rather than a producer-computed divergence verdict.
- **Credentials are references + scopes only.** Raw credential material is out of scope and should not appear in the event.
- **Content digests use `fingerprint`.** Local bytes such as adapters, schemas, policy bundles, and charters are represented using the same fingerprint vocabulary used by integrity attestations.
- **Hosted-model honesty.** When model bytes are not locally observable, use provider/name/version identity rather than inventing a local digest.
- **Admission/closure pair.** The same trust-base record shape is emitted before execution and again at closure. An unmatched admission is a structurally checkable gap.
- **Join, do not overlay.** Trust-base inventory records identity/custody. Invocation behavior belongs in activity events. Closure should correlate to those activity events instead of importing activity semantics into the inventory class.

## Evidence-grade implementation guidance emerging from the thread

These are useful implementation rules but should not be misrepresented as merged OCSF requirements:

1. **Integrity-protected correlation.** A closure/activity correlation key should be inside the event bytes protected by `record_integrity`, not carried only in external metadata. On current OCSF main, `attestation` covers the entire canonicalized event except its own `fingerprint` and `signatures`, so a present `metadata.correlation_uid` is within the integrity scope.
2. **Evidence-strength vocabulary.** The proposed `verification_id` vocabulary distinguishes Unknown, Locally computed, Provider asserted, Third-party attested, Not observable, and Other. This is descriptive; sufficiency remains consumer policy.
3. **Sampling configuration belongs in the declared/executed comparison.** The thread proposes carrying sampling controls and runtime binding in both halves so gateway/router rewrites are observable as evidence.
4. **Constraint source vs compiled form.** Source constraints represent what was approved; compiled constraints represent what ran. The delta may itself be evidence.

## Still open

- Final event-class name and `class_uid`.
- Exact Log / Collect / Change activity mapping for admission and closure.
- Final shape/name of `sampling_config` and whether some executed sampling belongs on `ai_operation` instead.
- Whether speculative-decoding fields are nested or flattened.
- Exact source-vs-compiled constraint representation.
- Final field name and placement of `verification_id`.
- The signature/key-id gap tracked separately upstream.

## Adjacent OCSF architecture

- `#1704` is consolidating AI outcome scalars under `ai_status` for the `ai_operation` profile.
- `#1754` is developing `AI Agent Activity` for agent-specific lifecycle/actions not already better represented by existing OCSF activity classes.
- Existing File System, Process, API, and other activity classes remain the preferred representation for actions already expressible in OCSF; AI context should be attached rather than duplicating the action taxonomy.

## Pilot consequence

Worldshepherd's pilot therefore treats the architecture as two planes:

- **Behavior plane:** OCSF activity events + `ai_operation` / `ai_status` / AI Agent Activity where appropriate.
- **Configuration/evidence plane:** #1724 trust-base inventory emissions with record integrity.

The planes are joined by correlation and common identity, not by duplicating each other's fields.
