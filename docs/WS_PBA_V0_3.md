# WS-PBA v0.3 — Power-Beaming Assurance

- **Status:** G1 reference implementation candidate
- **Date:** 2026-10-01
- **Owner:** Worldshepherd / SARA
- **Claim state:** `IMPLEMENTED IN SOFTWARE` for the bounded models, state-machine logic, and evidence-chain code in this branch; `REQUIRES LAB VALIDATION` and `REQUIRES PARTNER VALIDATION` for any physical power-beaming use.

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

## Evidence model

`PBAEvidenceEvent` records prior/requested/resulting state, the authorization identifier, normalized decision reason, configuration/navigation/tracking/interlock digests, sequence number, and the prior-event hash. `seal_event()` computes a domain-separated SHA-256 digest. `verify_chain()` rejects tampering, broken linkage, or sequence gaps.

This provides software evidence of decision provenance. It does not prove physical beam alignment, delivered power, endpoint position, hardware safety, or flight qualification.

## G1 validation scope

The branch test suite covers:

- prohibited shortcuts into delivery;
- nominal authorization;
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
- evidence-chain tamper detection and sequence-gap detection.

## G2 target

G2 is intentionally separate from G1. It should add cryptographic verification of authorization signatures, replay resistance, monotonic authorization sequence handling, signer/key policy, explicit adapter contracts, and adversarial sequence generation. Physical power-beaming claims remain out of scope until independent lab/partner validation exists.
