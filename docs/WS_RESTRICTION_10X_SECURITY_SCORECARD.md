# WS-RESTRICTION 10X SECURITY SCORECARD

Status: **ENGINEERING ACCEPTANCE TARGET / G4 VALIDATION PENDING**

## Baseline

The baseline is the best restriction pipeline present when the 10x directive was issued: protected-main G3.

A literal 10x claim is used only where a non-zero measurable baseline exists. For already-zero attack surfaces, the requirement is zero-tolerance non-regression rather than an undefined ratio.

## Executable G4 security metric

The cumulative required test now models six concrete residual attack classes that existed at the G3-start boundary:

1. caller-selected audit actor path;
2. authority absent from the hashed restriction payload identity;
3. outer audit actor mismatch accepted by observability;
4. semantic evidence mutation accepted without recomputing and checking restriction_id;
5. schema downgrade with a stale stronger-schema identity accepted;
6. HMAC fingerprints lacked a non-secret key-epoch identifier, making cross-rotation comparisons ambiguous.

Each open class counts as one residual-risk unit.

Baseline residual-risk units: **6**.

10x acceptance threshold: **<= 0.5 residual units**, i.e. **<=10% of baseline**.

Because attack-path count is integral, the cumulative G5 pass condition is **0/6 residual classes open**.

This is tested behaviorally in `test_restriction_10x_security.py`, not asserted from configuration strings.

## Zero-tolerance non-regression controls

G3 had already reduced these channels to zero, so they remain zero-tolerance:

- arbitrary free-form restriction summaries;
- arbitrary metadata on the registered internal policy-gate profile;
- any metadata or summary from unregistered source/processor pairs;
- caller-supplied context profile identifiers;
- raw-content replay/bypass remediation actions;
- raw restricted content in persisted evidence.

A future change that re-opens any zero-tolerance channel fails regardless of the aggregate score.

## What “10x more secure” does not mean

This scorecard does not claim ten times greater cryptographic strength, ten times lower real-world breach probability, FIPS validation, HSM assurance, or formal proof.

It means the selected measurable G3-start residual attack-path count must be reduced by at least one order of magnitude while all previously closed channels remain closed.

## Next 10x dimensions

Subsequent gates should use similarly measurable baselines:

- **G5 fingerprint-key epoch provenance:** implemented on the stacked G5 branch; ambiguous cross-rotation comparison paths must be zero before promotion;
- **G6 signer/witness assurance:** unsigned authority assertions -> independently verifiable signed/witnessed evidence;
- **G7 secret custody:** software/environment key custody -> external hardware-backed or independently managed custody where justified;
- **G8 adversarial validation:** predefined mutation/bypass corpus with quantified detection rate and false-negative budget;
- **G9 recovery:** measured mean/max recovery and evidence reconstruction time under injected corruption;
- **G10 external replication:** independent evaluator repeats the frozen protocol.

Claims advance only when those metrics are actually measured.
