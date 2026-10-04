# Worldshepherd Economic Authorization Gate v0.1

**Status:** DESIGN + DRY-RUN SOFTWARE GATE  
**Primary umbrella:** ACTIVE 1/3 — Platform & Assurance (#281)  
**Secondary dependency:** ACTIVE 3/3 — Growth & Externalization (#283)

## Purpose

This gate adds a protocol-neutral authorization layer for agent-initiated economic actions without enabling real-money execution.

The immediate implementation is deliberately narrow:

- represent an economic intent independently of a payment rail;
- bind the intent to a bounded session and explicit policy;
- enforce protocol, network, asset, payee, per-transaction, cumulative-budget, expiry, and human-approval controls;
- calculate a deterministic intent digest suitable for later PRIME SENTINEL signing/custody;
- fail closed for every `LIVE` payment request;
- perform no wallet access, signing, facilitator call, token transfer, card action, or settlement.

## Why this is the correct boundary

The external ecosystem has converged rapidly around agentic-payment infrastructure.

- x402 defines payment negotiation and settlement flows across transports such as HTTP, MCP, and A2A. Core x402 explicitly leaves client-side budget management outside the protocol specification.
- Amazon Bedrock AgentCore Payments already adds time-bounded payment sessions, spending limits, credentials, and observability around x402 and MPP.
- Google AP2 focuses on authenticated/verifiable intent and accountability for agent-initiated payments.
- Mastercard Agent Pay / Agent Pay for Machines includes credentialing, verifiable intent, permissioning, spending controls, and multi-rail settlement.
- Visa Trusted Agent Protocol focuses on cryptographically identifying trusted commerce agents and demonstrating authorized user intent.
- Stripe/Tempo MPP provides an additional HTTP-native machine-payment rail.

Therefore Worldshepherd should **not** claim generic budget controls, verifiable intent, agent identity, or agent-payment governance as unique inventions.

The defensible Worldshepherd differentiation is the integration of economic actions into the existing SARA / PRIME SENTINEL / ECHO SENTINEL LINK / OVERWATCH assurance architecture, with protocol-neutral policy, evidence custody, replay-resistant authorization, degraded-mode handling, claims control, and cross-domain mission governance.

## Architectural placement

```text
Human authority
      |
      v
PRIME SENTINEL
  policy / authorization
      |
      v
SARA
  economic intent orchestration
      |
      v
WS Economic Authorization Gate
      |
      +--> x402 adapter
      +--> AP2 adapter
      +--> MPP adapter
      +--> card/network adapter (future)
      |
      v
ECHO SENTINEL LINK
  intent + decision + receipt provenance
      |
      v
OVERWATCH
  spend / anomaly / state observability
```

v0.1 stops before every adapter.

## Implemented v0.1 controls

The pure evaluator in `worldshepherd_sara/economic_authorization.py` implements:

1. explicit session binding;
2. policy and intent expiry;
3. fail-closed rejection of future-dated intent;
4. explicit protocol allowlist;
5. explicit network allowlist;
6. explicit asset allowlist;
7. explicit payee allowlist;
8. per-transaction amount ceiling;
9. cumulative session-budget ceiling;
10. human-approval requirement;
11. deterministic SHA-256 intent digest;
12. unconditional denial of `LIVE` execution.

The evaluator has no external side effects.

## Required next gates

### G1 — Durable replay ledger

Add a SARA-owned or dedicated persistence layer for:

- unique `intent_id`;
- unique nonce;
- intent digest;
- authorization status;
- decision status;
- consumption status;
- failure status;
- protocol adapter receipt reference.

Replay of a consumed intent or nonce must fail closed.

### G2 — PRIME SENTINEL signature binding

Define a separate economic-authorization assertion signed by PRIME SENTINEL and bound to:

- intent digest;
- policy ID;
- session ID;
- maximum authorized amount;
- payee;
- protocol/network/asset;
- expiry;
- approval identity/reference;
- one-time nonce.

Private signing key custody must remain outside SARA.

### G3 — ECHO semantic provenance

Emit evidence records for:

- intent received;
- policy evaluated;
- decision;
- PRIME assertion verified;
- adapter request created;
- provider response;
- settlement/denial result;
- artifact or service delivered;
- reconciliation result.

Negative evidence and failures must be retained.

### G4 — Sandbox adapter

Implement exactly one external sandbox/testnet adapter. The first adapter must:

- contain no production credential;
- use a zero-value or test-only asset;
- prohibit mainnet/production destinations;
- be kill-switchable;
- produce deterministic evidence;
- demonstrate denial on policy mismatch, replay, expired authorization, destination mutation, and amount escalation.

### G5 — Cross-protocol conformance

Exercise the same Worldshepherd intent against at least two independent rails (for example x402 and MPP/AP2) and prove that the Worldshepherd policy/evidence semantics stay invariant even though the transport/payment representation differs.

## Claims boundary

Current claim after this gate:

**IMPLEMENTED IN SOFTWARE:** protocol-neutral dry-run economic-intent representation and fail-closed policy evaluation.

Not currently claimed:

- production payment execution;
- wallet custody;
- x402/AP2/MPP conformance;
- financial-services compliance;
- PCI, SOC, FedRAMP, CMMC, RMF, banking, money-transmitter, or other regulatory certification;
- partner validation;
- production security accreditation.

Those require separate evidence.
