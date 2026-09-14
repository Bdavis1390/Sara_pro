# QCRYPTO SARA → ECHO evidence synchronization

## Scope

The QCRYPTO runtime can synchronize one already-recorded, already-verified four-stage governance decision from SARA into ECHO SENTINEL LINK. This path is evidence transport only.

It does **not** execute a cryptographic migration, move value, sign blockchain transactions, grant live-value authority, establish Federal compliance, establish WS-CAE conformance, or make the current Ed25519 ECHO checkpoint post-quantum secure.

## Preconditions

SARA requires the supplied `decision_digest` to reconstruct a complete and internally consistent set of exactly four canonical stages:

- ECHO provenance state
- PRIME recommendation state
- SARA human-governance state
- OVERWATCH tracking state

Incomplete, inconsistent, authority-escalated, or malformed evidence is rejected before any ECHO forwarding attempt.

## Runtime boundary

The endpoint is:

`POST /admin/qcrypto/audit/echo-sync?decision_digest=sha256:<64-hex>`

It is admin-only. SARA forwards the four canonical audit records to ECHO `/v1/ingest`, then requests `/v1/reconcile` for the exact same bounded set. Success requires:

- `MATCHED = 4`
- `SARA_ONLY = 0`
- `ECHO_ONLY = 0`
- `PAYLOAD_MISMATCH = 0`

ECHO replay deduplication is accepted. Semantic conflicts fail closed. If ECHO is unavailable or not configured, SARA retains its durable local audit and records a pending synchronization event so the operation can be retried.

Synchronization bookkeeping uses `source_decision_digest`, not `decision_digest`, so sync events cannot become part of the original four-stage decision reconstruction.

## Deployment

The default SARA Compose service remains disconnected from ECHO. To enable the private bridge, use the base deployment together with `compose.qcrypto-echo.yaml` and the ECHO profile. The overlay:

- attaches SARA to `echo_private`;
- sets `ECHO_PERSISTENCE_URL=http://echo:9550`;
- mounts the ECHO ingest credential into SARA read-only at a separate path;
- does not expose ECHO private storage or checkpoint signing keys to SARA.

The forwarder permits cleartext HTTP only for loopback or the local Compose service name `echo`. Any off-box endpoint must use HTTPS. The forwarding credential must be an owner-controlled regular file with no group/other permissions and must be independent of SARA and PRIME credentials.

## Evidence classification

Once the exact implementation head passes both the QCRYPTO and full SARA validation gates, the software behavior may be labeled **PROVEN INTERNALLY** within the tested scope. Until then, new runtime synchronization behavior remains **IMPLEMENTED IN SOFTWARE / validation pending**.
