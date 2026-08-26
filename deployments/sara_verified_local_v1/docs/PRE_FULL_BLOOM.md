# PRE Full-Bloom Qualification Compiler

## Purpose

The full-bloom compiler turns frozen Worldshepherd synthetic/internal fixtures into machine-readable Qualification Evidence while preserving a strict claims boundary. It is intended for repeatable engineering readiness, regression testing, opportunity preparation, and evidence custody. It is not a government certification system and does not promote synthetic evidence into physical or operational claims.

## Run

From `deployments/sara_verified_local_v1` after `python -m pip install -e '.[test]'`:

```bash
rm -rf qualification_evidence
ws-pre-bloom \
  --fixtures fixtures \
  --out qualification_evidence \
  --software-commit "$(git rev-parse HEAD)" \
  --executed-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --operator "$(whoami)"
```

Equivalent module entry point:

```bash
python -m worldshepherd_sara.pre_bloom_cli --fixtures fixtures --out qualification_evidence --software-commit "$(git rev-parse HEAD)" --executed-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

## Exit behavior

Exit code `0` means every compiled Qualification Evidence record passed its frozen bounded test and every object in the local ECHO-style evidence store passed digest verification. A nonzero exit means the build must not be represented as qualification-pass evidence.

## Core outputs

- `qualification_index.json`: top-level bundle digests, failures, custody state, claims boundary, and Bloom extension summary.
- `*_qualification_bundle.json`: domain-specific frozen evidence bundles.
- `capability_readiness_ledger.json`: non-inheriting readiness rungs; a lower rung never implies a higher one.
- `capability_horizons.json`: 0–90 day, 3–12 month, and 12–24+ month preparation targets.
- `software_provenance.json`: source/build/output provenance. Current attestation is explicitly internal and unsigned.
- `echo_store/`: local hash-addressed custody objects with verification support.

## Current evidence domains

The compiler currently covers bounded internal software evidence for APNT operational-awareness logic, MBSE reconstruction benchmarking, IETM transformation, interpretable automated algorithm-discovery experiments, post-mission replay/proposal generation, multi-sensor fusion, RF simulation-to-measurement discrepancy accounting using synthetic data, CBM+/digital-twin health-state logic, manufacturing digital-thread lineage, DDIL transport fault campaigns, DDIL partition/rejoin conflict handling, and host-specific edge-runtime benchmarking.

Each domain retains its own claims boundary. Passing software tests do not establish Navy/DARPA/DoD acceptance, platform integration, hardware performance, material properties, RF performance, operational effectiveness, certification, clearance, CMMC status, NIST SP 800-171 conformity, or legal eligibility.

## Evidence interpretation rule

Use four separate questions:

1. **Source fact:** Is an external requirement verified by an authoritative source?
2. **Software behavior:** Did the bounded internal test execute and pass?
3. **Physical/partner evidence:** Has representative hardware, operational data, a partner system, or a controlled lab test produced evidence?
4. **External acceptance:** Has the relevant customer, assessor, regulator, lab, or certification authority accepted the evidence?

A YES to one question never supplies YES to another.

## CI contract

The repository workflow installs the package, compiles Python, runs the complete pytest suite, invokes `pre_bloom_cli`, verifies required output files and the ECHO store, uploads the qualification artifact, validates Docker Compose configuration, launches the ephemeral service, and executes the deployment verifier. A branch is not internally release-ready while this gate is red.

## Reproduction

For meaningful comparison, preserve:

- git commit SHA;
- fixture digests;
- exact output artifact;
- Python/runtime environment identity;
- execution timestamp and operator label;
- CI run identifier where applicable.

The compiler records the source commit and output digests. Current provenance is `INTERNAL_UNSIGNED`; external signing and independent reproduction remain separate future evidence gates.
