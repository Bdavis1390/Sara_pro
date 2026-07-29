# Security policy

## Supported deployment

Only the validated localhost package is supported. Public Internet exposure is not supported by this repository.

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
- No arbitrary command execution
- No outbound network discovery or broadcast behavior

The audit file is writable by the service account and therefore is not an
immutable or tamper-proof record. Protect the host and volume, restrict
operator access, and export logs to a separately controlled system if stronger
assurance is required.

## Reporting

Do not post credentials, private logs, personal information, or protected technical data in public issues. Revoke exposed tokens immediately and rotate both deployment credentials after any suspected compromise.
