# Worldshepherd upstream contribution pack — 2026-09-12

This directory contains contribution-ready technical proposals derived from Worldshepherd's implemented governance, audit, provenance, semantic-health, and bounded-automation patterns.

The artifacts are intentionally scoped to existing upstream issues rather than framed as replacement architectures.

## Active targets

1. **Open-RMF** — per-robot failure containment (#553) and Python GIL/concurrency liveness (#549).
2. **Eclipse Zenoh** — accept-path semantic health (#2780), silent-peer forwarding isolation (#2718), and metadata-only storage queries (#2783).
3. **Chainloop** — durable integration fan-out/replay semantics (#39), with compatibility guidance for merged adjudication fields from #3436.
4. **Keylime** — attestation truthfulness, cumulative failure history, and verifier cadence semantics (#1932/#1909/#1941).
5. **Sigstore/Cosign** — publication atomicity and source/target registry policy separation (#5035/#5037).
6. **Gazebo** — bounded observability and deterministic simulation qualification.
7. **Open Policy Agent** — minimal agent-runtime policy decision envelope and explicit PDP/PEP boundary (#8851).
8. **OpenTelemetry Semantic Conventions** — narrow interoperable audit-event envelope (#2468).

## Upstream-resolved lane

Eclipse Zenoh PR #2779 has merged an upstream fix for the peer-churn `StartConditions`/`ctrl_lock` deadlock related to #2637. Worldshepherd should retain any reproducer as validation evidence and monitor downstream adoption rather than submit a competing patch for that same root cause.

## Key artifacts

- `UPSTREAM_CONTRIBUTION_QUEUE.md` — current priority/status ledger.
- `CHAINLOOP_FANOUT_RESILIENCY_PROPOSAL.md` — durable fan-out design.
- `CHAINLOOP_3436_COMPATIBILITY_NOTE.md` — preservation of new adjudication outcome fields.
- `OPA_AGENT_POLICY_ENVELOPE.md` — bounded agent policy contract.
- `OTEL_AUDIT_EVENT_SEMCONV_PROPOSAL.md` — audit semantic-convention proposal.
- `ZENOH_2783_METADATA_ONLY_PROPOSAL.md` — backend-independent metadata-only storage-query contract.
- `patches/open-rmf-553-prevalidate-charger.patch` — Open-RMF #553 patch draft.
- `patches/zenoh-2780-incoming-permit.patch` — Zenoh #2780 hardening draft.

Additional patch/test artifacts live under `docs/oss_contributions/` and `external_anchor_pilots/`.

## Claims boundary

These documents include design contributions, test plans, and patch drafts. They do not claim upstream acceptance, conformance certification, production deployment in the upstream projects, or successful merge unless the referenced upstream repository itself shows that state.

Where Worldshepherd behavior is referenced, it is limited to software patterns already implemented or locally validated in `Sara_pro`. Patch drafts that require ROS 2, Zenoh stress infrastructure, hardware, or other unavailable upstream-specific environments remain explicitly labeled as requiring external validation.

## Contribution rule

Each proposal should provide:

- a narrowly defined problem;
- explicit state semantics;
- failure and recovery behavior;
- deterministic evidence/audit fields;
- testable invariants;
- a migration/compatibility path;
- an explicit claims state;
- a reason not to duplicate an already-merged upstream solution.
