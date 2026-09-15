# Security Policy

## Public-repository boundary

This repository is public. Do **not** open a public issue or commit content containing:

- passwords, API keys, tokens, private keys, certificates, recovery codes, or credentials;
- controlled unclassified information (CUI) or classified information;
- export-controlled technical data that is not cleared for public release;
- proprietary partner/customer data;
- private personal/contact information;
- production infrastructure details that would materially increase attack risk.

If sensitive information is exposed, revoke/rotate the affected secret or credential first. Git history should be treated as persistent even after a file is deleted.

## Supported security posture

Worldshepherd security work is evidence-gated. Repository workflows and documentation may implement or prepare controls related to scanning, provenance, rollback/recovery, NIST 800-171, CMMC/DFARS readiness, TLS architecture, configuration custody, and release attestation.

These artifacts **do not by themselves constitute certification, accreditation, government authorization, NIST conformity, CMMC status, DFARS satisfaction, or production security approval**.

## Reporting a vulnerability

If the issue can be disclosed safely without exposing sensitive details, open a GitHub issue with the minimum information needed to identify the affected component and request a private follow-up path.

Do not publish weaponizable exploit details, credentials, private infrastructure information, or sensitive partner data in the issue.

A useful initial report includes:

- affected path/component;
- affected commit/version;
- vulnerability class;
- security impact;
- minimal reproduction conditions;
- whether exploitation requires authentication or special access;
- proposed mitigation if known.

## Security engineering expectations

Changes affecting security boundaries should, where applicable, include:

- negative/denial tests;
- least-privilege review;
- authentication/authorization tests;
- input/schema validation;
- secret-handling review;
- audit/provenance behavior;
- rollback/recovery considerations;
- dependency/static-analysis results;
- explicit trust-boundary documentation.

## Claims boundary

Use `docs/CLAIMS_AND_EVIDENCE_POLICY.md` when describing security maturity. Internal tests support only the tested configuration and must not be converted into unsupported compliance or certification claims.
