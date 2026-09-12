# Cosign #5037 — source/target registry policy separation

Upstream: `sigstore/cosign#5037`
Status: design contribution / security boundary analysis
Claims state: SUPPORTED BY SOURCE REVIEW; IMPLEMENTATION NOT YET CLAIMED

## Source-reviewed problem

Current `pkg/oci/remote/options.go` stores one GGCR remote-option slice:

```go
type options struct {
    ...
    TargetRepository name.Repository
    ROpt             []remote.Option
    NameOpts         []name.Option
    OriginalOptions  []Option
    ...
}
```

`makeOptions()` initializes `ROpt` with the default keychain and
`WithRemoteOptions()` replaces that one slice. The same option state is then
used for source reads and for operations redirected to `TargetRepository`.

`pkg/oci/remote/remote.go` demonstrates the role mixing:

- `SignedEntity(ref, ...)` reads the source subject with `o.ROpt`.
- `suffixTag()` may read the source subject with `o.ROpt`, then produces a tag
  in `o.TargetRepository`.
- `signatures()` and `attestations()` construct a target reference and call
  `Signatures(..., o.OriginalOptions...)`, replaying the original option set.
- attachment readers similarly construct target references while carrying
  `OriginalOptions`.

When `COSIGN_REPOSITORY` points at a different repository/registry, the
reference role changes but the transport/auth policy can remain inherited.
Opaque `remote.Option` functions make it impossible to prove that inherited
state is safe for the target.

## Security invariant

**Repository redirection must never imply authorization-policy equivalence.**

The following values are role-bound unless equality has been explicitly proven:

- credentials and credential helpers;
- bearer tokens and repository-scoped tokens;
- mTLS client certificates/keys;
- CA pools and TLS server names;
- insecure/HTTP policy;
- custom `http.Client` or `RoundTripper` instances;
- retry/throttling clients that embed auth state;
- request middleware capable of adding headers.

A canonical-name match is necessary but not always sufficient for repository-
scoped authorization. Same host / different repository must therefore remain a
policy boundary unless maintainers deliberately define otherwise.

## Recommended public seam

Do not reinterpret existing `WithRemoteOptions` silently. Add an explicit target
policy channel with presence tracked separately from the slice value:

```go
type options struct {
    ...
    ROpt                 []remote.Option // existing source/compat policy
    TargetROpt           []remote.Option
    TargetROptExplicit   bool
    ...
}

func WithTargetRemoteOptions(opts ...remote.Option) Option {
    return func(o *options) {
        o.TargetROpt = append([]remote.Option(nil), opts...)
        o.TargetROptExplicit = true
    }
}
```

Presence must be distinct from length. An explicit zero-length target option
set can mean "use GGCR/default anonymous behavior" while absence means "the
caller did not choose a target policy". If maintainers want a named Cosign
keychain default, expose a separate option rather than overloading absence.

This seam is intentionally additive and compile-compatible.

## Redirect decision table

| Relationship | Source policy reuse | Recommended behavior |
|---|---:|---|
| Exact same canonical repository | compatible | Existing behavior may continue |
| Same registry, different repository | **not proven** | Require explicit target policy or an explicitly accepted compatibility mode |
| Different registry | **no** | Require independent target policy |
| DNS/CNAME alias | **no** | Do not infer equivalence from DNS |
| Mirror/redirect | **no** | Preserve configured role policy; do not follow identity assumptions into credentials |
| Explicit target options present | n/a | Use target options only for target operations |

## Fail-closed rule for opaque options

For a genuine redirect, opaque source `remote.Option` values cannot be audited.
The safest contract is therefore:

```text
redirect && source-options-opaque && !target-policy-explicit
    => fail before network mutation/read on target
```

If maintainers choose compatibility reuse instead, it should be an explicit
security trade-off documented and covered by tests; it should not be described
as isolation.

## Four-role model for copy

`copy` cannot be modeled as merely source + target. At minimum it has:

1. source subject read policy;
2. source redirected-artifact read policy;
3. destination subject/check policy;
4. destination artifact write policy.

Credentials from role 2 must never become role 4 credentials merely because an
option object is recursively reused.

This suggests that the long-term internal representation should use named role
objects instead of boolean target/source flags:

```go
type RegistryRolePolicy struct {
    Repository name.Repository
    RemoteOpts []remote.Option
    NameOpts   []name.Option
    Explicit   bool
}
```

The public API does not need to expose this type initially; it can be an
internal normalization target.

## Required test harness

Use two authenticated request-recording registries, A and B. Issue unique
credentials and TLS/client material per registry. Record every request method,
host, repository path, and authorization identity without logging raw secrets.

### Core isolation tests

1. Subject in A, `COSIGN_REPOSITORY` in B.
2. Source credential A succeeds on A and is deliberately rejected by B.
3. Target credential B succeeds on B and is deliberately rejected by A.
4. Assert no request to B carries A's identity/material.
5. Assert no request to A carries B's identity/material.

### Same-host/different-repository test

Use one registry host with repository-scoped tokens:

```text
registry.example/source/*  -> token S
registry.example/sig/*     -> token T
```

Prove that host equality alone does not authorize source-token reuse.

### Transport isolation tests

Independently configure:

- custom CA for A only;
- custom CA for B only;
- mTLS on A, not B;
- mTLS on B, not A;
- HTTP/insecure A versus TLS B;
- custom clients with sentinel request headers.

Sentinel headers provide a simple proof that a client or middleware did not
cross the role boundary.

### Error-preservation tests

Target errors must remain distinguishable:

- 401 authentication failure;
- 403 authorization failure;
- TLS verification failure;
- canceled context;
- deadline exceeded;
- transport failure;
- malformed claimed artifact.

None may be converted to "artifact absent" or trigger a successful legacy
fallback unless the code has positively identified an allowed not-found or
unsupported-referrers condition.

## Provenance / observability fields

For debugging without secret leakage, record role metadata rather than raw
credential details:

```text
registry.role = source_subject | source_artifact | destination_subject | destination_artifact
registry.repository = canonical non-secret repository identity
registry.policy.explicit = true|false
registry.auth.kind = keychain | explicit | anonymous | custom_client
registry.transport.kind = default | custom_ca | mtls | insecure_http | custom_client
```

These are diagnostic concepts, not a proposed OpenTelemetry namespace yet.

## Acceptance criteria

A contribution implementing #5037 should not be accepted until it proves:

- source credentials/clients never reach a distinct target role;
- target credentials/clients never reach source;
- same-host/different-repository is tested with scoped authorization;
- recursive constructors preserve role state explicitly;
- `OriginalOptions` cannot silently reintroduce source policy after role switch;
- caller-provided option slices are not mutated;
- 401/403/TLS/cancellation causes survive wrapping;
- diagnostics contain no credentials, tokens, client-cert private material, or
  raw authorization headers.

## Claims boundary

This document is a design/test contribution derived from the current Cosign
source and open issue #5037. It intentionally does not claim a code fix before
maintainers select the compatibility/fail-closed contract requested by the
issue.
