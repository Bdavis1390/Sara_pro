# Worldshepherd SARA

**A local-first reference implementation for bounded, evidence-producing automation.**

Worldshepherd's core engineering question is narrow:

> Can an automated system separate proposal, authorization, execution/recording, evidence, and operator visibility strongly enough that a human can tell what was allowed, what happened, and what remains unproven?

This repository contains the working SARA reference implementation plus broader Worldshepherd research artifacts. For an external systems review, **do not start with the broader research tree**. Start with the review surface below.

## External-review surface

1. [`docs/review/LINUS_TECHNICAL_REVIEW.md`](docs/review/LINUS_TECHNICAL_REVIEW.md) — the criticism we are asking for.
2. [`docs/review/ARCHITECTURE_AND_THREAT_MODEL.md`](docs/review/ARCHITECTURE_AND_THREAT_MODEL.md) — trust boundaries, assets, failure modes, and non-goals.
3. [`docs/review/REPRODUCIBILITY.md`](docs/review/REPRODUCIBILITY.md) — a clean-room review path.
4. [`docs/review/SECURITY_REVIEW_LOG.md`](docs/review/SECURITY_REVIEW_LOG.md) — flaws found before outreach, fixes, and residual limits.
5. [`docs/review/CLAIMS_BOUNDARY.md`](docs/review/CLAIMS_BOUNDARY.md) — what the repository does and does not establish.
6. [`deployments/sara_verified_local_v1/`](deployments/sara_verified_local_v1/) — the reviewable implementation.
7. [`deployments/sara_verified_local_v1/SECURITY.md`](deployments/sara_verified_local_v1/SECURITY.md) — the supported security boundary.

## 60-second architecture

The **architectural intent** is:

```text
proposal
   |
   v
SARA  -- intake/orchestration and durable local records
   |
   v
PRIME -- authorization boundary / signed release assertions
   |
   v
bounded action or local-only record
   |
   +--> ECHO-style evidence / provenance artifacts
   |
   `--> OVERWATCH-style operator visibility / health / audit
```

The **current reference implementation is intentionally narrower than that diagram**. The `/v1/relay` endpoint records an authenticated request locally; it does not execute an arbitrary command, discover external systems, broadcast, or activate a third party. That limitation is deliberate and reviewable.

## What is implemented today

The local reference service currently provides:

- localhost-oriented FastAPI administration and relay interfaces;
- separate relay and administrator bearer credentials with startup validation and constant-time comparison;
- liveness and persistent-storage readiness probes;
- request-size limits and restrictive HTTP response headers;
- administrator-only audit, registry, evidence, and self-test surfaces;
- protected registry namespaces that cannot be mutated through the generic registry patch endpoint;
- application-appended JSONL audit records with explicit acknowledgement that they are **not immutable or tamper-proof**;
- an optional PRIME SENTINEL signing boundary in which SARA verifies signed Ed25519 authorization assertions and does not receive the signer private key;
- exact signing-key fingerprint continuity checks for recorded PRIME authorizations;
- a deliberately single-writer local persistence boundary: one SARA writer process per writable SARA data volume;
- package tests, API tests, policy tests, qualification tests, adversarial/gap tests, and deployment verification under `deployments/sara_verified_local_v1/tests/`;
- CI paths for dependency resolution evidence, SBOM generation, vulnerability-advisory evidence, human-review triage evidence, claims-controlled qualification output, Docker Compose validation, backup/restore exercise, and observable release identity.

The implementation entry point is [`deployments/sara_verified_local_v1/worldshepherd_sara/app.py`](deployments/sara_verified_local_v1/worldshepherd_sara/app.py). The authentication boundary is [`auth.py`](deployments/sara_verified_local_v1/worldshepherd_sara/auth.py).

## Five-minute reviewer path

```bash
git clone https://github.com/Bdavis1390/Sara_pro.git
cd Sara_pro
git checkout review/linus-readiness-2026-09-14
cd deployments/sara_verified_local_v1

python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
pytest
```

Then inspect:

```bash
python -m compileall -q worldshepherd_sara
docker compose config --quiet
```

For the full local acceptance and recovery path, follow [`deployments/sara_verified_local_v1/docs/VERIFIED_DEPLOYMENT.md`](deployments/sara_verified_local_v1/docs/VERIFIED_DEPLOYMENT.md).

## What we want a skeptical reviewer to attack

The useful outcome is not endorsement. It is finding where this architecture is wrong, redundant, over-designed, or falsely reassuring.

Please try to break these assumptions:

- role separation cannot be bypassed through the HTTP/API surface;
- protected state cannot be mutated through an unintended generic path;
- authorization assertions cannot be replayed or confused across identities/environments or across signing-key replacements;
- evidence artifacts make their assurance limits obvious instead of implying certification;
- the system fails closed when required authorization or durable state is unavailable;
- the supported single-writer storage topology is represented accurately;
- the number of abstractions is justified by real isolation or evidence value.

If a simpler design provides the same security properties, that is a successful review result.

## Claims discipline

A green CI run is **internal software evidence**, not external certification. It does not by itself establish CMMC compliance, organizational NIST SP 800-171 conformity, RMF/ATO, FIPS validation, government interoperability, partner approval, field validation, legal chain of custody, or production HSM/KMS custody.

Similarly, the broader repository contains research, simulation, qualification, and opportunity artifacts with different evidence classes. Those should not be interpreted as demonstrated physical capability merely because they coexist with working software.

See [`docs/review/CLAIMS_BOUNDARY.md`](docs/review/CLAIMS_BOUNDARY.md) before making any external claim about the project.

## Security and disclosure

The supported deployment is local-only. Do not place credentials, CUI, classified information, export-controlled data, protected partner data, or operational mission data into this public repository, public issues, default fixtures, or GitHub Actions artifacts.

Security details: [`deployments/sara_verified_local_v1/SECURITY.md`](deployments/sara_verified_local_v1/SECURITY.md).

## Licensing status

This review branch does **not** invent or imply a repository-wide open-source license. Source is publicly inspectable, but a deliberate licensing decision is still required before presenting Worldshepherd itself as an open-source project or inviting code reuse under a specific license. See [`docs/review/LICENSE_DECISION.md`](docs/review/LICENSE_DECISION.md).

## External review principle

**Code first. Reproduction second. Criticism third. Partnership only if the first three survive.**
