# Reproducibility path

## Objective

A reviewer should be able to distinguish three things:

1. source that merely exists;
2. behavior exercised by automated tests;
3. claims that still require external validation.

This procedure focuses on the local SARA implementation and intentionally avoids relying on private infrastructure.

## Clean-room prerequisites

Expected host tools:

- Git;
- Python 3.11+ (CI currently exercises Python 3.12);
- Docker with Compose v2 for the container checks.

No production credentials are required. Use only synthetic/local test values.

## 1. Check out the review branch

```bash
git clone https://github.com/Bdavis1390/Sara_pro.git
cd Sara_pro
git checkout review/linus-readiness-2026-09-14
```

Record the exact commit under review:

```bash
git rev-parse HEAD
```

## 2. Install the narrow review target

```bash
cd deployments/sara_verified_local_v1
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
python -m pip check
```

The CI workflow uses pinned constraints for its stronger dependency-resolution evidence. A human review may use the commands above for convenience, but dependency differences should be recorded rather than ignored.

## 3. Compile and run the tests

```bash
python -m compileall -q worldshepherd_sara
pytest
```

A passing result means only that the checked-out code passed the included test suite in the reviewer's environment. It is not certification.

## 4. Inspect the main control points

Read these files before reading the broader repository:

```text
worldshepherd_sara/app.py
worldshepherd_sara/auth.py
worldshepherd_sara/prime_sentinel_authorization.py
worldshepherd_sara/prime_passport_api.py
worldshepherd_sara/storage.py
worldshepherd_sara/event_outbox.py
SECURITY.md
ops_policy.json
```

Questions to answer:

- Which caller-controlled values cross a trust boundary?
- Which state can relay authority mutate?
- Which state can only administrator authority mutate?
- Which state requires a purpose-specific governed API?
- What happens if storage, authorization, or the signer boundary is unavailable?
- Which evidence can a privileged local actor rewrite?

## 5. Validate container configuration

```bash
cp .env.example .env
# Replace required tokens with synthetic, distinct, random test values.
docker compose config --quiet
```

Do not commit `.env` or real credentials.

## 6. Full local acceptance path

For the repository's larger deployment sequence, follow:

```text
docs/VERIFIED_DEPLOYMENT.md
scripts/verify_deployment.sh
scripts/recovery_exercise.sh
scripts/ops_snapshot.sh
```

The corresponding CI workflow also generates dependency, SBOM, vulnerability-advisory, human-triage, qualification, partner-screening, recovery, and release-index evidence.

## 7. Negative tests a reviewer should add

The most valuable external tests are likely negative tests rather than more happy-path coverage. Suggested targets:

- malformed `Authorization` headers;
- token confusion between relay/admin/signing credentials;
- protected namespace mutation through alternate endpoints;
- symlink/path substitution against durable state;
- replay of a previously consumed authorization assertion;
- time-boundary tests around assertion expiry/not-before logic;
- environment/identity mismatch on signed authorization material;
- partial/corrupt outbox state at startup;
- audit/storage write failure after request acceptance;
- oversized/chunked request behavior without a trustworthy Content-Length;
- restart behavior after interrupted persistence;
- concurrent authorization/consumption attempts;
- downgrade or key-revocation behavior.

## 8. Report results precisely

Please report:

- commit SHA;
- host OS;
- Python and Docker versions;
- exact failing command/test;
- whether the issue violates an explicitly claimed property or reveals an undocumented assumption.

A minimal reproducer is preferable to a general description.

## Exit criterion for external outreach

External outreach should not describe this repository as "validated" merely because this procedure passes. The correct statement is narrower: **the review branch provides a reproducible local implementation and test/evidence paths suitable for independent technical criticism.**
