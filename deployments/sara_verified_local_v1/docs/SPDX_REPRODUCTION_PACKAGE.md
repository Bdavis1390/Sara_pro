# SPDX 3.0.1 Reproduction Package

## Purpose

This package turns the internally proven SPDX validation controls into a portable reproduction workflow that can be run outside GitHub Actions.

It is designed to make independent review **possible**. It does not make an execution independent merely because the script ran on another machine.

## Scope reproduced

The script `scripts/reproduce_spdx_validation.sh` reproduces three bounded observations against the frozen Worldshepherd SPDX 3.0.1 fixture:

1. **positive baseline** — the fixture passes canonical JSON Schema validation and canonical SHACL validation;
2. **structural negative control** — changing `SpdxDocument.profileConformance` from an array to a scalar is rejected by both AJV and `spdx3-validate`; and
3. **semantic negative control** — changing `CreationInfo.createdBy` to reference a `software_Package` remains JSON-Schema-valid but is rejected by SHACL because `createdBy` requires an `Agent`.

The package verifies the canonical SPDX 3.0.1 resources by SHA-256 before running any test:

```text
JSON Schema
582c64e809d5b3ef9bd0c4de13a32391b47b0284a3e8d199569fb96f649234b1

Ontology / SHACL
30ebb4af2d70a9809044ef46f44cc3dc5125226d70f818a50ed2e1d5f404c593
```

## Default reproduction

Prerequisites:

- `bash`;
- Python 3 with `venv` support;
- Node.js / npm;
- `curl`;
- `sha256sum`; and
- `git`.

From the repository root:

```bash
bash scripts/reproduce_spdx_validation.sh
```

By default the script:

- downloads the two versioned canonical SPDX 3.0.1 resources;
- refuses to continue if either resource digest differs from the pinned value;
- creates an isolated Python virtual environment;
- installs exactly `spdx3-validate==0.0.7` and `pyshacl==0.40.1`;
- installs `ajv-cli@5.0.0` in an isolated npm prefix;
- executes the positive, structural-negative, and semantic-negative controls; and
- writes logs, both negative-control documents, and `reproduction-receipt.json` under `spdx_reproduction_evidence/`.

The bootstrap tools are isolated from the SARA runtime environment. They are reproduction dependencies, not SARA product dependencies.

## Network-optional resource mode

A reviewer may cache the canonical SPDX resources and avoid fetching them during the test.

The resource directory must contain exactly these filenames:

```text
spdx-3.0.1-schema.json
spdx-3.0.1-model.ttl
```

Then run:

```bash
SPDX_REPRO_RESOURCE_DIR=/path/to/pinned-resources \
bash scripts/reproduce_spdx_validation.sh
```

The same pinned SHA-256 checks still run. A local file with the wrong digest is rejected.

## Preinstalled-tool mode

A reviewer that does not want the script to install validators can set:

```bash
SPDX_REPRO_BOOTSTRAP=0 \
SPDX3_VALIDATE=/absolute/path/to/spdx3-validate \
PYSHACL=/absolute/path/to/pyshacl \
AJV=/absolute/path/to/ajv \
VALIDATOR_PYTHON=/absolute/path/to/python \
bash scripts/reproduce_spdx_validation.sh
```

`VALIDATOR_PYTHON` should be the Python interpreter whose environment contains the `spdx3-validate` and `pyshacl` distributions so their installed versions can be recorded.

If an npm prefix is available, `AJV_ROOT` may also be set so the script can read the installed `ajv-cli` version directly.

## Receipt semantics

A successful run writes a receipt with:

- repository checkout commit;
- execution timestamp;
- canonical SPDX resource digests;
- baseline and negative-control input digests;
- Python / Node / validator versions;
- each bounded test result; and
- hard-false authority / endorsement fields.

The maximum automatic state is:

`REPRODUCTION_PACKAGE_EXECUTED`

The receipt always contains:

```text
independently_reproduced = false
reviewer_identity_established = false
general_spdx_conformance_established = false
community_endorsement_established = false
admission_authorized = false
release_approved = false
```

## What qualifies as outside reproduction

Worldshepherd should not upgrade this evidence merely because its own CI executes the script.

An attributable external reproduction should preserve, at minimum:

- reviewer identity or organization;
- exact repository commit checked out;
- operating system / environment details;
- generated `reproduction-receipt.json`;
- relevant validator logs;
- execution date; and
- any deviations from the documented procedure.

Those materials are evidence for later human assessment. They still do not automatically establish SPDX community endorsement or general product conformance.

## Claims state

`IMPLEMENTED IN SOFTWARE / PORTABLE REPRODUCTION GATE PENDING`
