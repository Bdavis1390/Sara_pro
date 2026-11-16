# WorldShepherd Claim-Evidence Gate — Standalone v0.2 Prototype

**Scope:** software-level validation of a structured research evidence envelope. It does not certify science, instrument calibration, operational security, mathematical correctness, originality, or independent replication.

**State:** candidate review implementation under #281 Platform & Assurance and #282 Science & Validation. Not installed in canonical SARA. The fixture is entirely **synthetic** and does not establish a physical RF effect.

## Reproduce the demo

Requires Python 3.12+ and its standard library. From the repository root:

```bash
python -m unittest discover -s tools/claim_evidence_gate/tests -v

PIN="$(cat tools/claim_evidence_gate/examples/PREREG_PIN.sha256)"
python tools/claim_evidence_gate/claim_gate.py \
  --prereg tools/claim_evidence_gate/examples/preregistration.json \
  --package tools/claim_evidence_gate/examples/package.json \
  --root tools/claim_evidence_gate/examples \
  --pinned-prereg-sha256 "$PIN" \
  --out /tmp/ws-claim-gate-audit.json
```

Expected synthetic example: 3 matching SHA-256 artifact digests, 2 self-declared passing synthetic control records, 1 inconclusive synthetic simulation record, and `integrity=PASS`. **This is structural consistency only.** All scientific result promotion still requires identified human review.

## Validated in the current prototype

- SHA-256 of declared artifact files matches claimed hashes.
- Preregistration canonical JSON digest matches the caller-supplied pin.
- Required control records exist, have verifiable artifacts and PASS outcomes; a failed run cannot be masked by a different passing run of the same required control.
- Summary event IDs and outcome totals reconcile with records.
- Rejects unsafe artifact paths (including traversal and symlink paths), malformed event fields, missing inputs, unexpected evidence classes and unsupported status promotions.
- Always reports `claim_automatically_proven: false`, `external_independence_verified: false` and `requires_human_review: true`.

## Explicitly NOT verified

- The in-repository example pin is *not* externally timestamped or independently anchored. Use a trusted separately retained preregistration digest for real experiments.
- `config_sha256` is **syntax checked only**; this version does not read and bind configuration bytes to the digest. This is a documented release blocker for operational use.
- Outcome PASS/FAIL labels are supplied by the record; the tool does not execute physical controls or prove test correctness.
- A string in `independent_attestation_anchor` is not verified as a cryptographic signature.
- File reads have a potential time-of-check/time-of-use race on hostile mutable filesystems; use immutable snapshots and stronger custody controls for untrusted sources.
- No environment, scientific method, calibration, measurement uncertainty, numerical convergence, mathematical proof, independent peer review, or lab instrumentation is checked.
- This prototype is not an approved production API and does not confer certification or compliance.

## Integration path

1. Validate exact-commit source through reviewable GitHub CI.
2. Bind run configuration and software environment to verified actual bytes.
3. Add an externally verified ECHO witness and preregistration freeze.
4. Separate structural integrity from scientific-domain validation gates.
5. Integrate into canonical SARA only after PRIME authorization contract and OVERWATCH reporting/rollback tests pass.

**Security:** public repository, synthetic fixtures only. Never commit original private Palace archives, unpublished laboratory raw data, partner IP, credentials, regulated material, or private contact details.
