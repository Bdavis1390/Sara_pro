# WS-CAE Deployment Guide

Status: research reference implementation

WS-CAE can be deployed as a read-only conformance checker for documented digital-asset authority profiles. The deployment surface performs no signing, key generation, wallet access, transaction construction, transaction broadcast, or asset movement.

## Local CLI

Requirements: Python 3.11+ and the two reference modules in `security/qcrypto/`.

Run a single profile or batch document:

```bash
python security/qcrypto/ws_cae_cli.py security/qcrypto/examples/ws_cae_reference_pair.json --pretty
```

Exit codes:

- `0` — input parsed and every profile passed the reference conformance checks;
- `1` — input parsed but one or more profiles are nonconformant;
- `2` — malformed input, missing/unknown fields, invalid JSON, or unreadable file.

Output is deterministic JSON and includes the profile count, per-profile assessment, maturity state, PQ authorization state, consensus boundary, and any issues.

## JSON profile contract

The machine-readable profile schema is:

`security/qcrypto/ws_cae_profile.schema.json`

The reference vocabulary currently includes:

- implementation maturity: `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, `MAINNET`;
- PQ authorization: `NONE`, `PLUGGABLE_AUTH_ONLY`, `PQ_NON_MAINNET`, `PQ_MAINNET`;
- consensus state: `CLASSICAL_OR_UNPROVEN`, `PQ_RESEARCH_OR_PARTIAL`, `PQ_DEPLOYED`.

Unknown fields fail closed in the reference CLI so an unrecognized claim cannot silently enter an assessment.

## Batch format

A batch document contains only a top-level `profiles` array:

```json
{
  "profiles": [
    {"...": "profile one"},
    {"...": "profile two"}
  ]
}
```

See `security/qcrypto/examples/ws_cae_reference_pair.json` for a working Algorand/Ethereum reference pair.

## GitHub Actions deployment

The repository includes a composite action at:

`.github/actions/ws-cae-conformance/action.yml`

Within this repository:

```yaml
- uses: actions/checkout@v4
- uses: ./.github/actions/ws-cae-conformance
  with:
    profile: security/qcrypto/examples/ws_cae_reference_pair.json
```

After the action is available on a stable public ref, another repository can invoke that ref and point `profile` at a JSON file in the caller workspace. Consumers should pin an immutable commit or release tag rather than a moving branch for reproducible assessments.

## Reference self-test

`.github/workflows/ws-cae-conformance-selftest.yml` runs the composite action against the reference pair whenever the deployable WS-CAE surface changes.

The ordinary QCRYPTO gate also runs unit tests for the CLI and reference classifier.

## Claims boundary

A passing WS-CAE profile means the documented authority state satisfies the reference conformance rules encoded by this research implementation. It does not establish:

- independent security certification;
- standards-body adoption;
- post-quantum consensus or validator security;
- wallet/custodian production approval;
- correctness of evidence supplied by a profile author;
- authorization to move live value.

Independent evidence review remains required for any operational or institutional use.
