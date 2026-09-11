# WS-SARA-EVAL-v1 — Evaluator Release Note

## Source baseline

The software source baseline under evaluation is fixed at:

`1c7be6c51ffd475f124e951f6c8c76208460b895`

The `ws-sara-eval-v1-freeze` branch may contain evaluator documentation added after that source baseline. Those documentation commits do **not** change the declared source baseline. Evaluators must record both the source baseline SHA and the evaluator-document bundle identity they received.

## Included software claim

This package supports evaluation of the bounded SARA / PRIME SENTINEL software behavior present at the source baseline, including the merged PRIME SENTINEL durable issuance ledger v1.5 and the verified-local deployment material present there.

## Explicit exclusions

This package does not silently include or validate:

- ECHO v1.6 / PR #153;
- W-RMABM G4 prep / PR #116;
- XTEND Certified candidate work;
- Sentinel infrastructure candidate branches;
- physical drone, humanoid, companion, materials, RF, propulsion, energy, quantum, or other hardware performance;
- customer/government acceptance;
- production certification;
- CMMC/NIST/DFARS conformity;
- classified suitability;
- HSM/KMS or immutable/WORM custody.

## Existing installation reference

The frozen deployment package documents a localhost-only interface, a Python virtual-environment quick start, Docker-based acceptance material, health/liveness/readiness surfaces, relay, audit, registry and self-test endpoints, and PRE evidence compilation. The evaluator should use only reviewed instructions and record any deviation.

## Evidence rule

A reproducible installation or green test run performed by Worldshepherd is still internal evidence. External-reproduction status requires an evaluator outside the development process to execute the agreed protocol in an evaluator-controlled environment and retain its original evidence.
