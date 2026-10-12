# v0.5 10x Target & Security Contract

“10x better / 10x more secure” is a target, not a present claim.

## Measurable advancement targets
A 10x performance claim requires a named baseline and at least one preregistered metric with >=10x measured improvement on identical held-out data (e.g. model-class search coverage per unit compute, falsification discrimination, or recovery error). No composite score may hide a regression.

## Security invariants
1. Physical execution is fail-closed: generated experiments are proposals only.
2. No eval/exec, shell invocation, network call, credential handling, or arbitrary expression execution in the discovery engine.
3. Explicit strain/frequency/temperature envelopes gate experiment proposals.
4. Evidence manifests are SHA-256 tamper-evident and chainable.
5. Claims state cannot be promoted by model output.
6. CI/test review precedes merge.
7. Public-repo boundary: no secrets, CUI, export-controlled or private partner data.
8. Invalid/non-finite trajectories fail validation.
9. Model disagreement drives bounded experiments; it never authorizes them.
10. “10x secure” requires comparative security evidence (attack surface, findings, exploitability, containment, or equivalent), not feature counting.

Current state: IMPLEMENTED IN SOFTWARE / SIMULATED ONLY. Physical validation remains required.
