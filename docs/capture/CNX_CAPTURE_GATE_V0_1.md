# Curious NerdworX Capture Gate v0.1

This utility turns the public federal-readiness ledger into a fail-closed machine check.

It distinguishes:

- **development readiness** — whether the bounded technical/capture package can proceed; and
- **submission readiness** — whether both development gates and every configured hard eligibility gate are closed.

The configuration contains only public status assertions. Do not place EINs, account data, credentials, CUI, clearance details, or other protected information in it.

## Examples

```bash
python tools/capture_gate.py SCAR_AOI03_TEAMING
python tools/capture_gate.py SCAR_AOI03_DIRECT --json
python tools/capture_gate.py XTECHSEARCH10_SUBMISSION --require-submission-ready
```

A blocked route is useful output. It tells SARA/PRIME which external dependency must be closed before a submission is authorized.

## Authority boundary

This gate is an internal control. It does **not** determine legal eligibility and never overrides:

- the solicitation;
- a contracting officer or program office;
- SAM.gov, SBA, DSIP, SPRS, DLA/JCP or other systems of record;
- legal/security/export-control review;
- a qualified partner's own representations.

The public configuration intentionally fails closed when documentary status is not established.
