# WS-PBA v0.3 — Power-Beaming Assurance

- **Status:** G1 merged/green; G2 cryptographic authorization and replay-hardening candidate
- **Date:** 2026-10-01
- **Owner:** Worldshepherd / SARA
- **Claim state:** `IMPLEMENTED IN SOFTWARE` for the merged G1 bounded models, state-machine logic, and evidence-chain code; G2 remains a branch candidate until CI passes and merge completes. Any physical power-beaming use remains `REQUIRES LAB VALIDATION` and `REQUIRES PARTNER VALIDATION`.

## Purpose

WS-PBA is a vendor-neutral mission-assurance layer for systems that transfer energy wirelessly between authenticated endpoints. It determines whether a requested operating-state transition is permissible under current policy and assurance evidence.

WS-PBA is **not** a beam controller, pointing system, RF beamformer, laser controller, orbital-guidance system, or physical targeting subsystem. Partner hardware remains responsible for physical actuation.

## Architectural boundary

```text
partner secure transport
        |
        v
normalized partner adapter
        |
        v
PRIME authorization -> SARA workflow/state custody
        |                         |
        v                         v
bounded permission          ECHO evidence
        |                         |
        +------------+------------+
                     v
                  OVERWATCH
```

Transport authenticity and mission authorization are separate controls. A cryptographically authentic message is not by itself permission to enter an energy-delivery state.

## State model

```text
SAFE_OFF -> DISCOVERY -> ATTESTED -> STATE_VALIDATION
    -> AUTHORIZATION_PENDING -> VERIFY_ONLY -> DELIVERY_AUTHORIZED

SAFE_HOLD is reachable from pre-delivery validation states.
DELIVERY_AUTHORIZED may only exit to RAMP_DOWN or FAULT_LATCHED.
RAMP_DOWN returns to SAFE_OFF or escalates to FAULT_LATCHED.
FAULT_LATCHED requires an explicit return to SAFE_OFF before a new sequence.
```

Direct transitions into `DELIVERY_AUTHORIZED` from `SAFE_OFF`, `DISCOVERY`, `ATTESTED`, `STATE_VALIDATION`, `AUTHORIZATION_PENDING`, `SAFE_HOLD`, `RAMP_DOWN`, or `FAULT_LATCHED` are prohibited.

## G1 invariants

1. Delivery requires a live `SafeToBeamAuthorization` whose bounded state is `DELIVERY_AUTHORIZED`.
2. Transmitter and receiver identities must match the authorization object.
3. Both endpoints must remain attested.
4. Configuration digest must match the authorized configuration.
5. Navigation and tracking inputs must remain valid and digest-bound.
6. Telemetry must be fresh.
7. Critical state disagreement blocks delivery.
8. A safety veto always overrides normal authorization.
9. Identity, configuration, or attestation loss during operation yields a latched fault disposition.
10. Navigation, tracking, freshness, or critical-state faults yield a controlled ramp-down disposition.
11. Every decision can be represented as a deterministic ECHO-compatible hash-chained evidence event.
12. Complete mission-local evidence chains begin at sequence zero; prefix truncation is rejected unless a future trusted checkpoint/anchor explicitly establishes a fragment start.

## Evidence model

`PBAEvidenceEvent` records prior/requested/resulting state, the authorization identifier, normalized decision reason, configuration/navigation/tracking/interlock digests, sequence number, and the prior-event hash. `seal_event()` computes a domain-separated SHA-256 digest. `verify_chain()` rejects tampering, broken linkage, sequence gaps, and untrusted truncated starts.

This provides software evidence of decision provenance. It does not prove physical beam alignment, delivered power, endpoint position, hardware safety, or flight qualification.

## G1 validation status

G1 merged through PR #526 after the repository's required test/build, CodeQL, SARA Verified Local, resilience, rollback, restore, NIST-precursor, freshness, and related CI workflows completed successfully.

The merged G1 test scope covers:

- prohibited shortcuts into delivery;
- nominal semantic authorization;
- transmitter and receiver attestation loss;
- stale telemetry;
- navigation and tracking invalidity;
- critical-state disagreement;
- configuration mutation;
- identity change;
- independent safety veto;
- receiver mismatch;
- configuration-digest mismatch;
- authorization expiry;
- evidence-chain tamper detection, sequence-gap detection, and prefix-truncation rejection.

## G2 cryptographic authorization boundary

G2 adds a verification-only Ed25519 trust boundary around `SafeToBeamAuthorization`. The canonical signature message binds:

- authorization and mission identifiers;
- transmitter and receiver identities;
- endpoint attestation evidence;
- configuration, navigation, and tracking digests;
- validity window and allowed operating state;
- policy and authority identifiers;
- signer key identifier;
- prior evidence-chain head;
- nonce; and
- monotonic authorization sequence.

A G2 verifier rejects missing, unknown, or revoked signer keys; invalid Ed25519 signatures; excessive authorization lifetime; authorizations that are too far in the future; not-yet-valid authorizations; and expired authorizations.

### Replay and rollback protection

`PBAReplayLedger` is a crash-persistent SQLite guard. After successful cryptographic verification it atomically rejects:

- reused `authorization_id` values;
- reused nonces; and
- sequence values that do not strictly increase for the same `(mission_id, transmitter_id, receiver_id)` scope.

The replay ledger uses `BEGIN IMMEDIATE`, `synchronous=FULL`, unique constraints, and a persisted highest-sequence record so replay/rollback protection survives process restart.

### Partner adapter contract

`PBAPartnerAdapter` is deliberately read-only. An adapter may return a normalized, timestamped `PBAAdapterEnvelope`; the protocol exposes no beam, pointing, targeting, waveform, or energy-actuation method. That keeps the Worldshepherd layer on the assurance side of the control boundary.

## G2 validation scope

The G2 branch tests cover:

- valid Ed25519 verification;
- signature tamper rejection;
- unknown-key rejection;
- revoked-key rejection;
- missing G2 key metadata rejection;
- duplicate authorization replay rejection;
- duplicate nonce rejection;
- non-monotonic sequence rejection across ledger restart;
- acceptance of a strictly higher sequence;
- expired and far-future token rejection; and
- conformance to the read-only partner adapter protocol.

G2 remains `IMPLEMENTED IN SOFTWARE — CANDIDATE` until its branch CI completes and the PR is merged. Physical power-beaming claims remain out of scope until independent lab and partner validation exist.
