# WS-CAE legacy QCRYPTO bridge

Status: repository-incorporation architecture note. This document does not promote capability maturity.

## Canonical interface

The standalone `ws_cae/` package is the canonical WS-CAE authority/continuity interface for new integrations. Its reusable GitHub action remains `.github/actions/ws-cae-conformance/action.yml` and invokes `python -m ws_cae.cli`.

## Preserved legacy/evidence lane

The earlier `security/qcrypto/` implementation is retained because it contains broader QCRYPTO research, risk, institutional-pilot, federal-readiness, migration-horizon, evidence-register, and legacy WS-CAE conformance material that is not equivalent to the standalone package.

Its legacy WS-CAE action is intentionally namespaced as `.github/actions/ws-cae-qcrypto-conformance/action.yml`, with a separate legacy self-test workflow. This prevents two different CLIs from sharing the same action identity.

## Compatibility rule

No output from one implementation is assumed conformant with the other solely because both use the WS-CAE name. Cross-implementation compatibility must be demonstrated with explicit fixtures, schema mappings, deterministic outputs, and retained evidence before any equivalence claim.

## Claims boundary

Both surfaces are read-only assessment/evidence software. Repository composition does not establish cryptographic migration execution, wallet/private-key custody, transaction signing/broadcast, movement of value, post-quantum security of a live chain, certification, regulatory compliance, standards-body adoption, chain endorsement, partner validation, or production deployment.
