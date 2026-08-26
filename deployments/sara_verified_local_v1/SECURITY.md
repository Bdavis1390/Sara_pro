# Security policy

## Supported deployment

Only the validated localhost package is supported. Public Internet exposure is not supported by this repository.

This public repository and its default local/CI workflows are approved only for synthetic, public, or otherwise explicitly releasable test data. Do **not** place CUI, classified information, export-controlled technical data, proprietary partner data, credentials, controlled government datasets, or operational mission data in this repository, GitHub Actions artifacts, public issues, fixtures, logs, or the default ECHO-style evidence store. Handling any such data requires a separately scoped and authorized environment, access-control model, contractual/security review, retention policy, and applicable encryption/audit controls.

## Security controls

- Separate relay and administrator bearer tokens
- Minimum token length and startup validation
- Constant-time token comparison
- Localhost-only Compose port binding
- Read-only container filesystem
- Dropped Linux capabilities and no-new-privileges
- Application-appended local audit records with restrictive file permissions
- Descriptor-based rejection of registry and audit symlink substitution
- Persistent-storage readiness verification
- Claims-controlled PRE qualification evidence and hash-addressed local evidence custody
- Synthetic DDIL/degraded-state and bounded authorization testing
- No arbitrary command execution
- No outbound network discovery or broadcast behavior

The audit file is writable by the service account and therefore is not an immutable or tamper-proof record. The ECHO-style content-addressed store detects local content mismatch but is likewise not a legal chain-of-custody system, government records system, WORM archive, or external attestation service. Protect the host and volume, restrict operator access, and export approved logs/evidence to a separately controlled system if stronger assurance is required.

## Compliance boundary

A green repository gate does not certify CMMC, organizational NIST SP 800-171 conformity, SPRS status, FedRAMP, RMF/ATO, FIPS validation, government interoperability, ITAR/EAR compliance, FOCI status, or security clearance. Those statuses require the applicable scoped environment and authoritative evidence. See `docs/COMPLIANCE_BOUNDARY.md`.

## Reporting

Do not post credentials, private logs, personal information, protected technical data, CUI, classified information, or export-controlled content in public issues. Revoke exposed tokens immediately and rotate both deployment credentials after any suspected compromise. If protected information is exposed, follow the applicable organizational/contractual incident procedure rather than attempting to preserve it in a public issue.
