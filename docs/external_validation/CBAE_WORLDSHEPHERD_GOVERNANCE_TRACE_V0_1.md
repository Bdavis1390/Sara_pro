# Worldshepherd ↔ CoSAI CBAE Public-Safe Governance Trace v0.1

**Status:** external review candidate  
**Claims posture:** IMPLEMENTED IN SOFTWARE / REQUIRES PARTNER VALIDATION, field by field as stated below  
**Repository snapshot:** `main` at `48ea5c8466946d7d1ac426f9658a7fed5b8a8a55`  
**External reference:** [CoSAI WS4 issue #146 — Capability-Bounded Autonomous Execution (CBAE)](https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/issues/146)

## Purpose

This document provides a small, public-safe trace for external technical review of the Worldshepherd governance architecture against the implementation-neutral CBAE pattern proposed in CoSAI Workstream 4.

It is **not** a claim that Worldshepherd conforms to CBAE, is independently assured, is tamper-proof, or has demonstrated containment of arbitrary autonomous agents. Its purpose is to make overlap, gaps, and falsifiable next tests explicit enough for an external reviewer to challenge.

The comparison is intentionally narrow. It uses the canonical local SARA package under `deployments/sara_verified_local_v1/` rather than research notes or future architecture claims.

## Current Worldshepherd implementation boundary

The following behaviors are present in the canonical public repository:

1. **Role separation.** SARA distinguishes `relay` and `admin` roles. Relay and administrator secrets must both be configured, must contain at least 24 characters, and must be different. Administrator-only routes reject a relay role.
2. **Bounded autonomy policy evaluation.** `autonomy_policy.py` evaluates an action candidate against an allowlist, deny list, confidence threshold, requested-authority ceiling, and reversibility requirement. The result is one of `AUTO_ELIGIBLE`, `HUMAN_REVIEW_REQUIRED`, or `DENIED` with reasons.
3. **Short-lived signed PRIME authorization for a specific release action.** `prime_sentinel_authorization.py` defines Ed25519-verifiable authorization assertions for `REQUALIFICATION_RELEASE`, including authorization ID, PRIME identity, target environment, issue/expiry times, nonce, key ID, and signature. Assertions are limited to a 15-minute maximum lifetime.
4. **Replay and key-revocation checks for that PRIME authorization path.** Unknown or revoked signing keys are rejected; expired assertions are rejected; duplicate authorization IDs and nonces are rejected when recorded; recorded authorizations can transition from `VERIFIED` to `CONSUMED` or `SUPERSEDED`.
5. **Protected governance state.** PRIME passport, PRIME authorization, and event-outbox registry namespaces cannot be changed through the generic registry patch endpoint; they must use governed APIs.
6. **Local action recording with correlation.** `/v1/relay` records a target, action, correlation ID, actor role, and payload-key names in the local audit. A successful relay response is explicitly `recorded_local_only`.
7. **Hash-linked HMAA mission evidence.** HMAA evidence records require a valid cryptographic event seal and the `previous_event_hash` must match the prior persisted event for the mission. The local evidence file is append-opened and fsynced.
8. **Evidence-oriented CI.** The protected SARA workflow compiles/tests the package and produces SBOM, vulnerability, human-triage, intake, qualification, partner-screening, recovery, operational snapshot, and release-index evidence with explicit claims-boundary assertions.

Important limitation: the ordinary SARA audit is application-appended local JSON Lines evidence and is explicitly documented as **not immutable, tamper-proof, or independently verified**. The HMAA chain provides stronger local chain-integrity semantics, but the local host is still inside the Worldshepherd trust boundary.

## CBAE property crosswalk

| CBAE property | Current Worldshepherd evidence | Assessment for this trace |
|---|---|---|
| 1. Explicit authority | Relay/admin roles; autonomy `requested_authority`; signed PRIME authorization for one bounded action and target environment | **PARTIAL — IMPLEMENTED IN SOFTWARE.** No general multidimensional capability lease yet. |
| 2. Independent enforcement | Protected SARA APIs and PRIME public-key verification enforce selected boundaries | **PARTIAL.** Verification exists, but the canonical verifier and workflow runtime remain within the same local SARA deployment boundary; independent enforcement outside the originating runtime is not established. |
| 3. Short-lived authorization | PRIME authorization has issue/expiry times and maximum 15-minute lifetime | **IMPLEMENTED IN SOFTWARE for `REQUALIFICATION_RELEASE` only.** Not generalized to all tool/effect actions. |
| 4. Positive-expansion authorization | Generic autonomy policy can force review when requested authority exceeds a ceiling | **PARTIAL.** There is no generic signed capability-delta lease across network/tool/data/secret/effect dimensions. |
| 5. Non-self-modifiable limits | Protected registry namespaces reject generic patching; governed APIs are required | **PARTIAL.** This protects application paths, not an independently administered external authority plane. Host/runtime administrator compromise remains outside this claim. |
| 6. Out-of-band termination | Key revocation can invalidate PRIME signing authority | **GAP.** No demonstrated independent kill path that revokes tools, egress, credentials, and execution of an arbitrary agent without cooperation from that runtime. |
| 7. Effect-bound evidence | Relay audit binds actor/action/correlation ID; HMAA provides cryptographically sealed hash-linked mission evidence | **PARTIAL.** No generic independently verifiable binding from workload identity + capability lease + policy decision to an actual external-effect receipt. |
| 8. Freshness and replay resistance | PRIME checks expiry, future skew, key revocation, duplicate authorization IDs, and nonce reuse; HMAA checks chain continuity | **PARTIAL / STRONG OVERLAP.** Workload-identity continuity and generalized lease replay semantics remain missing. |
| 9. Finality gating | Human-review disposition and bounded release authorization exist in specific paths | **GAP for generic irreversible effects.** There is no universal fresh authorization check immediately before arbitrary high-impact external commitment. |
| 10. Falsifiable containment | CI, self-test, recovery exercises, explicit claims boundaries, and policy-evaluator reasons are testable | **PARTIAL.** CBAE-specific unauthorized-egress, authority-delta, kill-latency, finality, and common-mode degradation test suite is not yet implemented. |

## Public-safe test vector A — policy refuses automatic authority expansion

This test uses only the existing policy evaluator semantics.

### Candidate

```json
{
  "action_id": "trace-a-001",
  "action_type": "external_effect.demo",
  "confidence": 0.99,
  "requested_authority": 3,
  "reversible": false,
  "payload": {
    "demonstration": true
  }
}
```

### Policy

```json
{
  "policy_id": "public-safe-local-only-v1",
  "allowed_auto_action_types": ["local.record"],
  "denied_action_types": [],
  "minimum_auto_confidence": 0.95,
  "maximum_auto_authority": 0,
  "require_reversible_for_auto": true
}
```

### Expected disposition

`HUMAN_REVIEW_REQUIRED`

Expected reasons include:

- action type is not in the automatic-execution allowlist;
- requested authority exceeds the automatic-execution ceiling;
- automatic execution requires reversible action.

The high model/candidate confidence does **not** grant authority. This is an important Worldshepherd invariant: confidence and authority are separate variables.

## Public-safe test vector B — a signed PRIME release assertion cannot be silently generalized

The existing signed PRIME assertion schema authorizes only:

```text
action = REQUALIFICATION_RELEASE
```

and binds that authorization to a named `prime_id`, `target_environment`, issuance window, nonce, signing key and signature.

Therefore an otherwise valid PRIME assertion for requalification release must **not** be represented as authorization for `external_effect.demo`, arbitrary network access, arbitrary tool execution, or an unrelated irreversible effect.

This is both a strength and a gap:

- **strength:** the current authorization object is deliberately narrow rather than a bearer token with undefined ambient authority;
- **gap:** Worldshepherd does not yet expose a general CBAE-style capability envelope for arbitrary agent actions.

## Minimum-record interoperability experiment

CBAE issue #146 proposes an independently verifiable minimum evidence record. The table below maps those fields onto the closest current Worldshepherd representation without upgrading claims.

| CBAE minimum field | Closest Worldshepherd field | Current status |
|---|---|---|
| `workload_identity` | `prime_id` or authenticated SARA actor in selected paths | **Not equivalent.** Generic workload identity continuity is missing. |
| `capability_lease_id` | `authorization_id` | **Available only for the bounded PRIME authorization path.** |
| `lease_expiry` | `expires_at` | **Implemented for PRIME authorization.** |
| `revocation_epoch_or_pointer` | signing `key_id` plus configured revoked-key set | **Partial.** Key-level revocation exists; per-lease revocation epoch/pointer is not established. |
| `policy_version` | `policy_id` in autonomy policy, plus release/config identity elsewhere | **Fragmented.** Not yet one signed/effect-bound policy-version field. |
| `requested_tool_or_service` | relay `target`/`action` or PRIME action/target environment | **Partial and path-specific.** |
| `decision` | autonomy disposition; PRIME `VERIFIED`/`CONSUMED`/`SUPERSEDED` states | **Implemented in separate paths; not unified.** |
| `external_effect_id_or_hash` | HMAA `event_hash` can identify evidence events | **Not equivalent.** Generic external-effect receipt is missing. |
| `receipt_parent_id` | HMAA `previous_event_hash` | **Strong structural overlap, but currently a separate evidence stream.** |
| `timestamp` | authorization issue/expiry and evidence `recorded_at` timestamps | **Available.** |
| `signer` | PRIME `key_id` and SHA-256 public-key fingerprint; HMAA seal semantics | **Available in selected paths.** |

## Proposed interoperability envelope — NOT YET IMPLEMENTED

The next useful implementation experiment is a small adapter record, not a replacement architecture:

```json
{
  "schema": "WS-CBAE-INTEROP-TRACE-V0.1",
  "workload_identity": null,
  "capability_lease_id": "<prime authorization_id when applicable>",
  "lease_expiry": "<expires_at when applicable>",
  "revocation_pointer": "<key_id / future lease revocation reference>",
  "policy_version": "<policy_id or immutable policy digest>",
  "requested_tool_or_service": "<bounded action target>",
  "decision": "<permit|review|deny>",
  "external_effect_id_or_hash": null,
  "receipt_parent_id": "<prior evidence hash when applicable>",
  "timestamp": "<UTC>",
  "signer": "<key fingerprint when applicable>",
  "worldshepherd_correlation_id": "<correlation id>",
  "claims_boundary": "No external effect or CBAE conformance is claimed unless independently verified."
}
```

The nulls are intentional. A missing externally verifiable workload identity or external-effect receipt must remain visibly missing rather than being filled with a convenient local identifier.

## External-review questions

External collaborators are invited to challenge these points specifically:

1. Is the PRIME authorization object close enough to a capability lease to justify a narrow interoperability adapter, or would that conflate fundamentally different security objects?
2. What minimum workload-identity primitive should be bound to the authorization without coupling Worldshepherd to one cloud/IAM stack?
3. Should per-authorization revocation be added in addition to signing-key revocation, and what freshness model is sufficient for disconnected/degraded operation?
4. Can HMAA's hash-linked evidence be used as `receipt_parent_id` without falsely implying that the local evidence store is independently trusted?
5. What enforcement boundary should produce `external_effect_id_or_hash` so the originating runtime cannot fabricate success?
6. What finality gate is required before a bounded action becomes externally irreversible?
7. Which CBAE containment tests can be reproduced entirely in a public local harness without requiring privileged infrastructure?

## Acceptance criteria for the next implementation step

No conformance claim should be made until a public test harness can demonstrate at least:

- expired authorization rejection;
- revoked signing-key rejection;
- nonce/authorization replay rejection;
- policy denial and human-review escalation with machine-readable reasons;
- evidence-chain rejection when the parent hash is wrong;
- explicit failure when workload identity is absent where required;
- explicit failure when an external effect lacks an enforcement-bound receipt;
- no use of `recorded_local_only` as evidence that an external effect occurred;
- a documented trust-boundary statement identifying which component can still tamper with local evidence;
- independent reviewer feedback recorded as accepted, rejected, or unresolved against each mapping above.

## Claims boundary

This trace supports only the following statements:

- Worldshepherd has **implemented software** for bounded policy evaluation, role separation, short-lived signed authorization in a specific release path, replay checks in that path, protected governance namespaces, correlation-based local relay recording, and hash-linked sealed HMAA evidence.
- Worldshepherd has **not demonstrated CBAE conformance**, independent authority-plane enforcement, generic workload identity continuity, universal out-of-band termination, universal finality gating, or independently verified external-effect receipts.
- External review is being sought specifically to determine whether the overlapping mechanisms can interoperate without overstating assurance.

That distinction is the experiment.