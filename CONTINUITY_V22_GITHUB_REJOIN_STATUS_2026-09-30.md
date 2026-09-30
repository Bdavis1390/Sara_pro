# Worldshepherd V22 — GitHub Rejoin Status

Date: 2026-09-30

## Decision

**GITHUB ACCESS RESTORED — CONTROLLED-BUILD FORWARD-PORT CANDIDATE**

V22 does not overwrite the V21 recovery runtime. It forward-ports the highest-value Yellow-Hat supply-chain controls onto the live `Bdavis1390/Sara_pro` protected-main tree.

## Baseline observed before forward-port

- Repository access: restored with push/admin capability through the connected GitHub application.
- Default branch: `main`.
- Observed main commit at audit start: `6f8781209b51bbb03786e813be28554c5a537cd5`.
- The live SARA Dockerfile is already digest-pinned and differs from the frozen V21 recovery copy, so it is preserved.
- The live `constraints-runtime.txt` contains exact current runtime versions and is preserved.
- The live `pyproject.toml` intentionally retains compatibility ranges; V22 verifies that all direct runtime dependencies are constrained by the exact runtime constraint set rather than replacing those ranges.

## V22 forward-port

- Adds a fail-closed pip resolver-report verifier.
- Requires exact constraint coverage of the complete resolved runtime graph.
- Requires a SHA-256 for every remote resolved artifact.
- Emits a replayable `--require-hashes` candidate lock.
- Emits deterministic CycloneDX 1.7 candidate SBOM evidence.
- Builds the exact current SARA wheel and Docker image in GitHub Actions.
- Verifies that the Docker base remains digest-pinned.
- Uploads PR evidence under read-only permissions.
- Uses GitHub/Sigstore SLSA provenance only after a reviewed push reaches `main`.

## Claims boundary

**IMPLEMENTED AS A REVIEW CANDIDATE.** No GitHub CI result is treated as independent production validation by itself. Existing Worldshepherd external-evidence gates remain authoritative.
