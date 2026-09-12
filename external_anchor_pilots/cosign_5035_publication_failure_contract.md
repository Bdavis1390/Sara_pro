# Cosign #5035 — publication failure contract and fault-injection model

Upstream: `sigstore/cosign#5035`
Status: design contribution / source-reviewed recovery model
Claims state: SUPPORTED BY SOURCE REVIEW; IMPLEMENTATION NOT YET CLAIMED

## Scope

This document does **not** duplicate the immediate local-layout ordering fix
tracked by Cosign #5030 / PR #5031. It addresses the broader #5035 question:
what Cosign can truthfully promise when an OCI publication consists of several
registry mutations and one of them fails.

## Source-reviewed observations

`pkg/oci/remote/write.go` contains multiple publication shapes with different
commit points:

- `WriteSignatures` / `WriteAttestations`: GGCR image write to a mutable tag.
- `WriteSignaturesExperimentalOCI`: subject `HEAD`, signature layer writes,
  config write, then artifact-manifest `PUT`.
- `WriteReferrer`: subject `HEAD`, config write, all layer writes, then
  artifact-manifest `PUT` (manifest-last).
- `WriteSignedImageIndexImages`: index/image writes, legacy signature and
  attestation writes, then local-layout referrer processing. The reviewed code
  currently writes empty config, then the referrer manifest, then referenced
  bundle layers in that local-layout block; #5030/#5031 address this immediate
  ordering defect.

A manifest-last writer reduces invalid-manifest failures but does **not** make a
multi-object operation transactional. Earlier blobs or manifests can already be
durable when a later step fails.

## Non-negotiable invariant

**Never claim rollback unless the registry protocol provides a scoped operation
that can be proven to affect only state owned by the current invocation.**

Completed content-addressed blobs are not invocation-owned merely because this
invocation uploaded them: the digest may have existed beforehand or may be
shared by another manifest. Generic deletion is therefore not rollback.

## Publication state machine

Represent each writer as an ordered set of observable phases, not as a boolean
success/failure:

```text
VALIDATE
   |
   v
SUBJECT_RESOLVE          (optional/read-only)
   |
   v
BLOB_PUBLISH*            (config + N layers)
   |
   v
ARTIFACT_MANIFEST_PUBLISH  <-- digest-addressed commit point
   |
   v
DISCOVERY_INDEX_UPDATE     (optional mutable fallback/tag/index)
   |
   v
COMPLETE
```

Legacy mutable-tag writers have a different commit point:

```text
VALIDATE -> GGCR_BLOB_WORK -> MUTABLE_TAG_MANIFEST_PUBLISH -> COMPLETE
```

Multi-object workflows such as `cosign load` should be modeled as a sequence of
publication units, each with its own commit point. A later unit failing does not
rewind an earlier unit.

## Failure result model

Avoid flattening all failures into `error` text if maintainers are willing to
add structured internal state. A useful internal record is:

```go
type PublicationPhase string

const (
    PhaseValidate       PublicationPhase = "validate"
    PhaseSubjectResolve PublicationPhase = "subject_resolve"
    PhaseBlobPublish    PublicationPhase = "blob_publish"
    PhaseManifest       PublicationPhase = "artifact_manifest_publish"
    PhaseDiscovery      PublicationPhase = "discovery_index_update"
)

type PublicationProgress struct {
    Phase              PublicationPhase
    Processed          []v1.Descriptor
    ManifestCommitted  bool
    DiscoveryCommitted bool
}
```

The public API need not expose this exact type. The key requirement is that
error wrapping preserve:

1. original cause (`errors.Is` / `errors.As`);
2. failed phase;
3. whether a digest-addressed manifest was already committed;
4. non-secret descriptor identities that successfully completed.

Do not include authorization headers, registry credential material, raw client
certificates, or registry response bodies that may contain secrets.

## Retry semantics

Idempotence must be claimed per operation, not per high-level command.

### Generally safe to retry

- content-addressed blob upload for an already-known digest;
- digest-addressed artifact-manifest publication when byte-identical and the
  registry accepts the same digest;
- reads/HEAD operations.

### Requires conflict semantics

- mutable `.sig` / `.att` tag replacement;
- fallback referrers indexes implemented as read-modify-write;
- any tag used as a discovery index;
- multi-object load/copy workflows.

For these surfaces, retry needs a conditional-write or read/merge/conflict-loop
contract. "Retry the command" is not equivalent to idempotence.

## Discovery partial success

A critical state is:

```text
artifact manifest committed = true
discovery fallback update   = failed
```

That should be reported as **partial success**, not total failure implying
nothing exists. Recovery should first probe for the digest-addressed artifact,
then repair only the missing discovery/index state.

This avoids re-uploading content unnecessarily and gives operators a truthful
answer about registry state.

## Upload-session cancellation boundary

If a registry exposes an upload-session UUID/capability that is demonstrably
owned by the current invocation, canceling that *incomplete upload session* may
be safe.

That does not authorize deletion of:

- completed blobs;
- artifact manifests;
- mutable tags written earlier;
- discovery indexes shared with other writers.

Treat session cancellation as transport cleanup, not transaction rollback.

## Fault-injection matrix

Build a request-recording fake registry with deterministic failpoints. Each
mutating request receives a monotonically increasing operation number and can
be configured to fail before or after persistence.

Test every writer with failures at:

| Phase | Before persistence | After persistence / lost response |
|---|---:|---:|
| config blob | required | required |
| each layer blob | required | required |
| artifact manifest | required | required |
| mutable tag manifest | required | required |
| fallback discovery GET | required | n/a |
| fallback discovery PUT | required | required |

The "persisted but client saw failure" case is essential: networks can drop the
response after the registry commits. Recovery logic must therefore probe state
instead of assuming an error means no mutation happened.

### Additional dimensions

Repeat relevant failpoints with:

- blob already existed before invocation;
- blob newly uploaded by this invocation;
- same digest referenced by another artifact;
- deletion unsupported;
- deletion forbidden;
- cancellation during upload;
- 401 and 403;
- TLS failure;
- context cancellation / deadline;
- connection reset / EOF;
- fallback index concurrent update conflict.

## Lost-update test for fallback indexes

Two publishers concurrently start from index revision R0:

```text
P1: read R0 -> add artifact A
P2: read R0 -> add artifact B
P1: write R1(A)
P2: write R1(B)
```

An unconditional second write loses A. The accepted contract should require
one of:

- conditional request / ETag / digest precondition;
- conflict detection and bounded read-merge-retry;
- native OCI referrers API where available.

A test passes only if both A and B remain discoverable or one writer returns a
preserved conflict that can be safely retried.

## Error taxonomy

Keep at least these classes distinguishable through wrapping:

```text
VALIDATION
AUTHENTICATION          (401)
AUTHORIZATION           (403)
NOT_FOUND               (only proven 404 semantics)
UNSUPPORTED_REFERRERS
CONFLICT
CANCELED
DEADLINE
TLS
TRANSPORT
REGISTRY_PROTOCOL
MANIFEST_REJECTED
DISCOVERY_UPDATE_FAILED
```

A 401/403/TLS/cancellation error must never be recast as "not found" to trigger
legacy fallback.

## Observability / provenance

For operator-safe diagnostics, an event can include:

```text
publication.writer
publication.phase
publication.unit_id
publication.descriptor.digest
publication.manifest_committed
publication.discovery_committed
publication.retry_attempt
publication.error_class
```

Do not log token values, authorization headers, client-key material, or complete
registry error bodies without sanitization.

## Acceptance criteria

A #5035 implementation should prove:

1. all locally knowable validation occurs before the first mutation;
2. all manifest-referenced blobs are published before manifest publication;
3. original causes survive wrapping and are testable with `errors.Is/As`;
4. failure reports identify the last successful commit point;
5. no completed shared blob is deleted as generic rollback;
6. retries are only called idempotent where tested/proven;
7. fallback discovery updates are conflict-safe;
8. artifact-manifest success + discovery failure is represented truthfully as
   partial success/recoverable discovery state;
9. fault injection covers both pre-commit failure and lost-response-after-
   commit cases;
10. logs/errors contain no registry credentials or secret-bearing headers.

## Claims boundary

This is a design and validation contribution based on Cosign's current writer
implementations and open issue #5035. It does not claim that the cross-writer
contract has been accepted upstream or that every registry implements the same
cleanup capabilities.
