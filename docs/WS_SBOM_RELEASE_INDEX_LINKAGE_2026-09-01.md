# WS SBOM Release-Index Linkage — 2026-09-01

## Purpose

This patch converts software supply-chain visibility from a standards-readiness target into a CI-generated evidence artifact.

It adds an internal SBOM evidence generator and links the resulting artifact into the SARA release evidence index.

## Added

- `worldshepherd_sara/sbom_cli.py`
  - Adds `ws-sbom-evidence`.
  - Reads `dependency-freeze.txt`.
  - Emits:
    - `software-sbom.json`
    - `sbom-evidence-summary.json`
  - Digests the dependency freeze, `pyproject.toml`, runtime constraints, and CI constraints.
  - Preserves a strict claims boundary.

- `tests/test_sbom_cli.py`
  - Verifies dependency-freeze parsing.
  - Verifies SBOM summary schema, component count, input digests, and claims boundary.
  - Verifies CLI output files.
  - Rejects missing dependency-freeze input.
  - Blocks false supply-chain readiness language.

- `release_index_cli.py`
  - Adds required `--sbom-dir`.
  - Adds `software_sbom_evidence` to release-index artifacts.
  - Records local evidence paths and digests for:
    - `software-sbom.json`
    - `sbom-evidence-summary.json`
  - Records SBOM component count, input-file digests, and evidence status.

- `.github/workflows/sara-verified-local-v1.yml`
  - Installs and checks `ws-sbom-evidence`.
  - Generates `sbom_evidence_ci`.
  - Uploads `software-sbom-evidence`.
  - Links SBOM artifact ID, digest, and URL into `sara-release-evidence-index`.

## Generated files in CI

```text
sbom_evidence_ci/
  software-sbom.json
  sbom-evidence-summary.json
```

## Evidence status

```text
INTERNAL_CI_GENERATED_UNSIGNED
```

This status means CI generated and retained a software supply-chain evidence artifact. It does not mean the SBOM is complete, hermetic, independently verified, externally reproduced, legally reviewed, or accepted by a partner or authority.

## Release-index additions

The release index now includes:

```json
{
  "artifacts": {
    "software_sbom_evidence": {
      "name": "software-sbom-evidence",
      "artifact_id": "...",
      "artifact_digest": "sha256:...",
      "artifact_url": "..."
    }
  },
  "local_evidence": {
    "sbom_summary_path": "sbom_evidence_ci/sbom-evidence-summary.json",
    "sbom_summary_sha256": "sha256:...",
    "software_sbom_path": "sbom_evidence_ci/software-sbom.json",
    "software_sbom_sha256": "sha256:...",
    "sbom_component_count": 0,
    "sbom_evidence_status": "INTERNAL_CI_GENERATED_UNSIGNED"
  }
}
```

## Claims boundary

This patch does not establish:

- complete or hermetic SBOM coverage;
- vulnerability scan pass;
- vulnerability remediation;
- license legal review;
- SLSA compliance;
- CMMC conformity;
- NIST SP 800-171 implementation;
- DFARS satisfaction;
- FedRAMP authorization;
- ISO certification;
- SOC 2 attestation;
- supplier approval;
- partner validation;
- external reproduction;
- field performance;
- hardware performance;
- classified access;
- operational authority.

## Standards effect

This closes one concrete evidence gap under the standards-control matrix: software supply-chain inventory is now generated during CI and carried into the release evidence index.

It does **not** promote any standards-control record to `MET` or `EXCEEDED`. Formal status promotion remains blocked until the control matrix has the required evidence, assessment result, gap disposition, and external/formal assessment references where required.
