# WS-QX Evidence-First Roadmap

## 0.1 — current release candidate
Common evidence envelope, claim interlocks, WS-SEMCAP profile, schema, tests, PRE delta template, claims matrix.

## 0.2 — DDIL and replay/resynchronization
Add WS-DDIL-01 profile, deterministic link impairment manifests, stale/replay evidence controls, receiver resynchronization metrics, and evidence-chain continuity tests.

## 0.3 — hardware/HIL adapter contract
Rebase the useful G3 hardware-facing concepts onto current main: channel identity, units, ranges, calibration validity, clock provenance, safe defaults, E-stop requirements, raw/normalized retention, uncertainty budgets. Dangerous physical fault modes remain emulated unless a reviewed safe test fixture exists.

## 0.4 — cryptographic custody
Evaluate signed manifests, trusted timestamping, hardware/software attestation, append-only evidence roots, and separation of operator identity from authorization. No production-security claim until threat-model testing exists.

## 0.5 — external replication package
Define exportable blind-test bundles with immutable inputs, declared metrics, environment capture, expected evidence schema, and independent result import without allowing self-attestation to count as external replication.

## 1.0 — qualification exchange
Stable profile/version semantics, machine-readable Requirement Delta Records, evidence graph, PRIME promotion policy, OVERWATCH readiness view, and reproducible partner/test-lab exchange package.
