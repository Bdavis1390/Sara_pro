# WS-CAE Deployment Guide

Status: research reference implementation

WS-CAE can be deployed as a read-only conformance checker for documented digital-asset authority profiles. The deployment surface performs no signing, key generation, wallet access, transaction construction, transaction broadcast, or asset movement.

## Local CLI

Requirements: Python 3.11+ and the WS-CAE reference modules in `security/qcrypto/`.

Run a single profile or batch document:

```bash
python security/qcrypto/ws_cae_cli.py security/qcrypto/examples/ws_cae_reference_pair.json --pretty
```

Apply an independent relying-party policy to the same chain profile:

```bash
python security/qcrypto/ws_cae_cli.py \
  security/qcrypto/examples/ws_cae_reference_pair.json \
  --policy security/qcrypto/examples/ws_cae_interop_minimum_policy.json \
  --pretty
```

Exit codes:

- `0` — input parsed and every profile passed the reference checks and, when supplied, the consumer policy;
- `1` — input parsed but one or more profiles are nonconformant or fail the selected consumer policy;
- `2` — malformed input, missing/unknown fields, invalid JSON, unreadable file, or malformed policy.

Output is deterministic JSON and includes profile count, per-profile assessment, maturity state, PQ authorization state, consensus boundary, issues, and optional policy results.

## Profile and policy contracts

The machine-readable schemas are:

- `security/qcrypto/ws_cae_profile.schema.json` — facts asserted about an ecosystem or authority surface;
- `security/qcrypto/ws_cae_policy.schema.json` — requirements chosen by a custodian, exchange, wallet, auditor, treasury, or other relying party.

The reference vocabulary includes:

- implementation maturity: `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, `MAINNET`;
- PQ authorization: `NONE`, `PLUGGABLE_AUTH_ONLY`, `PQ_NON_MAINNET`, `PQ_MAINNET`;
- consensus state: `CLASSICAL_OR_UNPROVEN`, `PQ_RESEARCH_OR_PARTIAL`, `PQ_DEPLOYED`.

Unknown profile or policy fields fail closed so unrecognized claims or requirements cannot silently enter an assessment.

## Adoption model

A chain does not need to be post-quantum ready before publishing a WS-CAE profile. A truthful `ROADMAP`, `DRAFT`, `DEVNET`, or `NONE` state is still useful because relying parties can see the current boundary instead of reconstructing it independently.

The chain publishes one neutral profile. Different consumers can then apply different policies without asking the chain to maintain separate security questionnaires.

For example:

- an integration team may accept `DEVNET + PLUGGABLE_AUTH_ONLY` for experimental work;
- an institutional policy may require `MAINNET + PQ_MAINNET` for high-value account authorization;
- consensus/validator PQ state remains independently visible in both cases.

See:

- `security/qcrypto/examples/ws_cae_chain_profile_template.json`;
- `security/qcrypto/examples/ws_cae_interop_minimum_policy.json`;
- `security/qcrypto/examples/ws_cae_institutional_pq_policy.json`.

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
    policy: security/qcrypto/examples/ws_cae_interop_minimum_policy.json
```

The `policy` input is optional. A chain can use the action only to validate its published profile, while downstream consumers can reuse the same action with their own policy file.

After the action is available on a stable public ref, another repository can invoke that ref and point `profile` and optional `policy` at files in the caller workspace. Consumers should pin an immutable commit or release tag rather than a moving branch for reproducible assessments.

## Reference self-test

`.github/workflows/ws-cae-conformance-selftest.yml` exercises both the reference conformance path and the consumer-policy path against the Algorand/Ethereum reference pair whenever the deployable WS-CAE surface changes.

The ordinary QCRYPTO gate also runs unit tests for the CLI, consumer policy, and reference classifier.

## Adoption and procurement material

- `WS_CAE_ADOPTION_CASE.md` explains why publishing a profile has low integration cost and can reduce duplicated due diligence.
- `WS_CAE_RELYING_PARTY_REQUIREMENTS.md` provides neutral procurement/due-diligence language and explicitly accepts equivalent evidence to avoid lock-in.

## Claims boundary

A passing WS-CAE profile means the documented authority state satisfies the reference conformance rules encoded by this research implementation. A passing consumer policy means only that the supplied profile satisfies that selected policy.

Neither result establishes:

- independent security certification;
- standards-body adoption;
- post-quantum consensus or validator security unless separately evidenced;
- wallet/custodian production approval;
- correctness of evidence supplied by a profile author;
- regulatory compliance;
- authorization to move live value.

Independent evidence review remains required for operational or institutional use.
