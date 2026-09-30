# Worldshepherd V22 GitHub-rejoin controlled build

V22 forward-ports the Yellow-Hat supply-chain lane onto the live `Bdavis1390/Sara_pro` protected-main tree after GitHub access restoration.

## Design

* `main` remains the source of truth; recovery copies do not overwrite newer runtime files.
* Pull requests run with `contents: read` and generate **candidate** resolver, hash-lock, CycloneDX 1.7 SBOM, Docker/base-image, and build-manifest evidence.
* The resolver must match every exact package in `deployments/sara_verified_local_v1/constraints-runtime.txt` and every remote artifact must carry a SHA-256 from the pip resolver report.
* The generated hash lock is replayed with `pip --require-hashes`.
* A reviewed push to `main` may generate GitHub/Sigstore SLSA provenance for the evidence bundle through `actions/attest`; pull-request jobs do not receive OIDC or attestation write permissions.
* CI evidence is not automatically production evidence. Independent verification and the remaining external Worldshepherd gates remain mandatory.

## Claims boundary

**IMPLEMENTED IN CI / CONTROLLED-BUILD CANDIDATE.** The workflow does not claim production readiness, independent validation, trusted time, off-host anti-rollback anchoring, hardware-backed signer custody, measured-boot attestation, or independent adversarial assessment.
