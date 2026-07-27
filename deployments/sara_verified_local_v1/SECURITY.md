# Security policy

## Supported deployment

Only the current approved release on localhost is supported. Public Internet exposure is not supported by this repository.

## Security controls

- Separate relay and administrator bearer tokens
- Minimum token length and startup validation
- Constant-time token comparison
- Localhost-only Compose port binding
- Read-only container filesystem
- Dropped Linux capabilities and no-new-privileges
- Durable append-only audit records
- No arbitrary command execution
- No outbound network discovery or broadcast behavior

## Reporting

Do not post credentials, private logs, personal information, or protected technical data in public issues. Revoke exposed tokens immediately and rotate both deployment credentials after any suspected compromise.
