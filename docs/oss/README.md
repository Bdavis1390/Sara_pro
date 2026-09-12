# Worldshepherd upstream contribution pack — 2026-09-12

This directory contains contribution-ready technical proposals derived from Worldshepherd's implemented governance, audit, provenance, and bounded-automation patterns.

The artifacts are intentionally scoped to existing upstream issues rather than framed as replacement architectures.

## Targets

1. **Chainloop** — durable integration fan-out / replay semantics for chainloop-dev/chainloop#39.
2. **Open Policy Agent** — minimal policy decision envelope and PDP/PEP boundary for open-policy-agent/opa#8851.
3. **OpenTelemetry Semantic Conventions** — narrow interoperable audit-event envelope for open-telemetry/semantic-conventions#2468.

## Claims boundary

These documents are design contributions. They do not claim upstream acceptance, conformance certification, production deployment in the upstream projects, or successful merge. Where Worldshepherd behavior is referenced, it is limited to software patterns already implemented or locally validated in Sara_pro.

## Contribution rule

Each proposal must provide:

- a narrowly defined problem;
- explicit state semantics;
- failure and recovery behavior;
- deterministic evidence/audit fields;
- testable invariants;
- a migration path that preserves existing behavior where practical.
