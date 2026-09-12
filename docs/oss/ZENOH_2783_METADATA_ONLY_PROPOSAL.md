# Zenoh #2783 — metadata-only storage query proposal

Upstream target: `eclipse-zenoh/zenoh#2783`

Claims state: **DESIGN CONTRIBUTION CANDIDATE / NOT IMPLEMENTED UPSTREAM / REQUIRES MAINTAINER REVIEW**

## Problem

Zenoh storage queries currently return the full stored `Sample`. For large images, point clouds, model artifacts, or other binary payloads, clients cannot cheaply ask whether a key exists, whether its HLC timestamp is fresh enough, or how large the payload is before transferring it.

The proposed upstream feature is a metadata-only selector mode. The strongest contribution is to define the wire-level contract before backend-specific optimizations are added.

## Proposed contract

Use one reserved selector parameter owned by the storage-manager plugin, for example:

```text
_meta_only=true
```

A metadata-only reply should preserve the identity and timing semantics of the stored sample while omitting the original payload bytes.

### Reply requirements

```text
key_expr:       unchanged
kind:           unchanged
encoding:       defined behavior; see below
timestamp:      exact stored HLC timestamp
payload:        zero bytes
attachment:     metadata envelope
```

Recommended metadata envelope:

```json
{
  "zenoh.storage.meta.version": 1,
  "payload_len": 1234567,
  "original_encoding": "application/octet-stream",
  "original_attachment": "<opaque-preserved-value-if-present>"
}
```

The exact serialization should follow Zenoh conventions chosen by maintainers; the important requirement is semantic stability.

## Design constraints

### 1. Backend-independent behavior first

The initial implementation should live at the storage-manager layer if practical so filesystem, RocksDB, S3, and future backends expose the same behavior without each implementing their own selector semantics.

Backend-specific fast paths can be added later, provided they are observationally equivalent.

### 2. Do not overload an empty payload

An actually stored zero-length payload must remain distinguishable from a metadata-only response. The reply therefore needs an explicit metadata-mode marker/version, not just `payload == empty`.

### 3. Preserve HLC exactly

Freshness checks are a primary use case. Metadata-only mode must return the exact stored timestamp rather than generating a new reply timestamp that could be mistaken for data freshness.

### 4. Preserve attachment semantics without recursion

If the original sample has an attachment, the metadata response should preserve it in a defined field or side structure. Avoid recursively embedding an envelope that itself looks like a normal application attachment without a version marker.

### 5. Define encoding behavior

The response payload is metadata, not the original application object. Returning the original encoding while sending an empty payload can be misleading. Two viable options for maintainer review:

- keep reply `encoding` as the original encoding and make `_meta_only` authoritative; or
- use a defined metadata encoding and expose `original_encoding` in the metadata envelope.

The second option is semantically cleaner, but compatibility should drive the final choice.

### 6. Selector namespace

The reserved selector must not collide with backend/application query parameters. The storage manager should either reserve a clearly documented prefix or reject ambiguous duplicate forms.

## Suggested processing path

```text
query arrives
   |
   +-- normal query --------------------> existing backend path
   |
   +-- metadata-only requested
          |
          v
      resolve stored sample
          |
          v
      capture original length/timestamp/encoding/attachment
          |
          v
      strip payload before wire serialization
          |
          v
      return metadata response
```

The critical bandwidth property is that stripping occurs before serialization/transmission, not after receipt by the client.

## Acceptance tests

### Common behavior

1. Store a non-empty binary payload with timestamp and attachment.
2. Normal `get` returns the original payload unchanged.
3. Metadata-only `get` returns zero original payload bytes.
4. `payload_len` equals the original byte length exactly.
5. HLC timestamp equals the normal stored sample timestamp exactly.
6. Original attachment is preserved according to the documented contract.
7. A zero-length stored value is distinguishable from metadata-only mode.
8. Missing keys preserve normal not-found/query behavior.
9. Unknown selector parameters preserve existing compatibility behavior.

### Cross-backend matrix

Run the same logical tests against:

```text
filesystem
RocksDB
S3
```

A backend-specific optimization passes only if its externally visible result matches the generic storage-manager implementation.

### Large-payload bandwidth test

Store a payload large enough to make accidental transfer obvious (for example tens of megabytes). Capture transmitted bytes or instrument serialization and assert that metadata-only mode does not serialize/transmit the original payload.

### Concurrency/freshness test

Update the same key while alternating metadata-only and normal queries. Assert that each response's HLC timestamp and `payload_len` correspond to one coherent stored version; do not allow timestamp from one version and length from another.

## Worldshepherd relevance

This feature has direct value for semantic-health and provenance workflows:

- check whether remote evidence is newer before transfer;
- inspect image/point-cloud size before downloading over DDIL links;
- validate that stored telemetry exists and is recent without paying payload cost;
- gate retrieval by policy using timestamp/size metadata;
- distinguish repository/process liveness from actual fresh data availability.

Those use cases support the design, but the upstream interface should remain generic Zenoh functionality with no Worldshepherd-specific namespace.

## Non-goals

- no new authorization bypass;
- no claim that metadata proves payload integrity unless a digest is separately provided and verified;
- no backend-specific API exposed to clients;
- no mutation of stored samples;
- no claim of upstream acceptance until maintainers review the contract.
