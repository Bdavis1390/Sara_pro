# Worldshepherd Research Wave 3 — Execution Queue

Status: INTERNAL EXECUTION PLAN / CLAIMS-GATED

Parent intake: `WS-RI-2026-0904-W3`

## Priority order

### P1 — `WS-QE-2026-PRI-001` Prime-basis ablation

Reason: lowest-cost disconfirming test and no external dependency.

Required controls:
- fixed PDE/multi-physics benchmark
- identical data split and compute budget
- prime-indexed representation versus at least one standard representation
- predeclared metrics: error, convergence, stability, conditioning, compute cost, energy residual, thermal residual
- retain null/negative result

Exit state:
- `SIMULATED ONLY` if a reproducible software benefit is established
- remain `HYPOTHESIS` if benefit is absent or inconclusive

### P2 — `WS-QE-2026-ADM-001` SSPADAWANZZ current-main differential audit

Reason: historical source reports a useful role-separated admin interface, but the exact historical marker set was not found in the current default-branch search during intake.

Audit questions:
- what current code provides operator/admin role separation?
- what current code provides audit read access and registry mutation controls?
- are historical scripts/endpoints obsolete, renamed, or absent?
- are secrets excluded from logs and evidence bundles?
- can any historical requirement be satisfied by the current architecture without reintroducing obsolete code?

Exit state:
- explicit implemented/missing/superseded matrix
- no historical claim generalized to current `main`

### P3 — `WS-QE-2026-EMB-001` Programmable EM boundary benchmark

Reason: establishes whether the proposed signed-coupling/control model produces useful bounded field-shaping behavior before hardware expenditure.

Software phase:
- finite tile array
- phase/amplitude state
- bounded material-state abstraction
- passive control article
- beam/null/scattering objective
- thermal drift sensitivity
- configuration and result provenance

Bench phase only after software evidence supports it:
- small reconfigurable array/coupon
- calibrated baseline and reconfigured measurements
- repeatability and uncertainty

Exit state:
- software results remain `SIMULATED ONLY`
- physical claim requires separate lab evidence

### P4 — `WS-QE-2026-ALT-001` WS–AlTi modeling/coupon package

Reason: highest physical-resource dependency and explicit IP/legal dependency.

Pre-coupon gates:
- prior-art/IP review
- composition/process design space
- process-window model
- manufacturing configuration custody
- measurement plan and acceptance metrics

Coupon gates:
- chemistry/microstructure
- mechanical/thermal/electrical properties as applicable
- repeatability/process variation
- negative evidence retained

Exit state:
- no physical maturity increase without coupon measurements
- no valuation/patentability conclusion without independent evidence and legal review

## Cross-cutting provenance rule

Every execution item follows:

`requirement/hypothesis -> test -> configuration -> result -> uncertainty -> pass/fail/inconclusive -> provenance -> identified-human review`

No execution item may set partner, certification, field, flight, or operational validation by internal software result alone.
