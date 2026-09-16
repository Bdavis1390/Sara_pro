# Zenoh #2784 — bounded cancellation and native-operation ownership

Upstream issue: `eclipse-zenoh/zenoh#2784`

Reviewed upstream main: `646f2d1b730e584a570015a77bee9f6db08be9d1`

Claims state: **SOURCE-REVIEWED HARDENING DESIGN / REQUIRES MAINTAINER API DECISION + RUST/LINUX VALIDATION**

## Problem statement

Issue #2784 reports that session construction can be cancelled while native hostname resolution or credential-file operations remain blocked. The caller can stop waiting, but cannot prove that every operation owned by the cancelled session has drained. That distinction matters for deterministic shutdown, restart containment, and resource ownership.

The governing invariant for this contribution lane is:

> **A cancellation/timeout must not be reported as cleanup completion unless all work owned by that operation has either completed, been synchronously cancelled, or remains represented by an explicit drain/ownership handle.**

A timeout that merely drops a Rust future is not enough.

## Current-source audit

### 1. Resolver path remains native-resolution backed

Current Zenoh link implementations still call `tokio::net::lookup_host(...)` in the TCP, UDP, WebSocket, TLS, and QUIC address-resolution paths.

Examples include:

```rust
// zenoh-link-tcp
let iter = tokio::net::lookup_host(address.as_str().to_string()).await?;
```

and:

```rust
// TLS / QUIC
match tokio::net::lookup_host(address.as_str()).await?.next() {
    Some(addr) => Ok(addr),
    None => bail!(...),
}
```

This gives the caller an async interface, but it does not by itself prove that dropping/cancelling the waiting future synchronously terminates the underlying native resolver work.

### 2. TLS and QUIC root-CA file paths still perform synchronous file I/O

Both the TLS and QUIC trust-anchor helpers use the synchronous standard-library path:

```rust
if let Some(filename) = config.get(TLS_ROOT_CA_CERTIFICATE_FILE) {
    let mut pem = BufReader::new(File::open(filename)?);
    let trust_anchors = process_pem(&mut pem)?;
    root_cert_store.extend(trust_anchors);
    return Ok(Some(root_cert_store));
}
```

Those helpers are called from async TLS/QUIC configuration construction. A special file such as a FIFO can therefore block the runtime thread directly while the configuration future is being polled.

### 3. Private-key and certificate paths use `tokio::fs::read`

The key/certificate helpers already use:

```rust
tokio::fs::read(value).await
```

This avoids direct synchronous reads on the async executor, but it still does not establish the stronger issue requirement that cancellation joins or terminates the underlying blocking/native file operation. A caller timeout can bound how long the caller waits without proving that the blocking worker has drained.

## Failure classes must be kept separate

### A. Executor blocking

A synchronous operation executes directly in an async task and can stall an executor thread.

Current example: TLS/QUIC root-CA `File::open` + buffered PEM read.

### B. Detached or non-joined blocking work

The async task stops waiting, but an OS/native/blocking-pool operation that it initiated may continue running after cancellation.

Potential examples: native resolver work and asynchronous filesystem helpers implemented on blocking workers.

### C. Caller timeout without ownership closure

`timeout(operation).await` returns at the deadline, but the timeout only bounds the caller. If the underlying work is not cancellable/joined, the system must not describe that as a drained shutdown.

A correct fix must state which of A/B/C it addresses.

## Recommended staged contribution

### Phase 0 — deterministic regression fixtures first

Before changing production behavior, add tests that distinguish caller completion from owned-work completion.

Required fixtures:

1. **Credential FIFO fixture**
   - configure TLS/QUIC `root_ca_certificate_file` as a FIFO with no writer;
   - start session/link construction;
   - cancel the owning operation;
   - independently observe whether the credential operation remains outstanding.

2. **Controlled resolver fixture**
   - inject or otherwise control hostname resolution so it can be held past the caller cancellation deadline;
   - cancel session construction;
   - prove whether native resolver ownership has actually drained.

3. **Executor responsiveness control**
   - while the bad credential path is blocked, schedule an unrelated short runtime task;
   - prove whether the runtime thread remains able to make progress.

Tests should report two timestamps separately:

```text
caller_cancel_complete
owned_native_work_drained
```

They must not collapse them into one "timeout passed" assertion.

### Phase 1 — remove direct synchronous trust-anchor I/O from async construction

Convert `load_trust_anchors` in TLS and QUIC to an async/in-memory path so PEM parsing happens after bytes have been obtained without a direct blocking `File::open` on the executor.

Conceptually:

```rust
async fn load_trust_anchors(config: &Config<'_>) -> ZResult<Option<RootCertStore>> {
    ...
    if let Some(filename) = config.get(TLS_ROOT_CA_CERTIFICATE_FILE) {
        let bytes = tokio::fs::read(filename).await?;
        let mut pem = Cursor::new(bytes);
        let trust_anchors = process_pem(&mut pem)?;
        ...
    }
}
```

This phase removes the known executor-blocking defect. It **must not** be presented as a complete cancellation-ownership fix, because an async filesystem helper may still rely on blocking work that outlives the cancelled waiter.

A project-level decision is needed on whether credential "file" configuration should accept non-regular files at all. If FIFOs/devices are not part of the supported contract, rejecting non-regular credential paths before reading them is a legitimate fail-fast hardening option and would make shutdown semantics substantially easier to reason about. Symlink handling and cross-platform behavior need explicit tests if such a rule is adopted.

### Phase 2 — make resolver ownership explicit

The resolver path needs a separate design decision.

Options for maintainers to evaluate:

1. **Keep native resolution, document non-cancellable ownership** and expose a drain state/handle so close does not claim complete cleanup prematurely.
2. **Introduce an injectable resolver abstraction** so the default may remain native while tests and deployments can use a resolver with explicit cancellation semantics.
3. **Adopt a fully async resolver implementation** if the dependency/behavior trade is acceptable.
4. Preserve a **numeric-address fast path** that performs no DNS work.

Do not replace `lookup_host` merely to satisfy the test without defining cache behavior, `/etc/hosts` behavior, search domains, IPv4/IPv6 ordering, and platform compatibility.

### Phase 3 — define the public cancellation contract

Zenoh should make one of these contracts true and testable:

**Contract A — synchronous drain**

```text
close/cancel returns only after every operation owned by the construction attempt has terminated.
```

or:

**Contract B — explicit asynchronous drain ownership**

```text
close/cancel returns a state/handle that distinguishes "caller no longer waits" from "all owned work drained".
```

The existing behavior should not be described as Contract A unless the native/blocking work is proven to terminate within the bound.

## Acceptance matrix

The eventual upstream fix or design should cover at least:

1. numeric IPv4 TCP locator — no resolver work; normal open/close succeeds;
2. hostname TCP locator — successful resolution remains compatible;
3. held resolver — cancellation does not falsely claim drained ownership;
4. normal regular root-CA file — TLS open succeeds;
5. malformed regular root-CA file — fails deterministically;
6. FIFO root-CA path with no writer — cannot indefinitely block an async executor thread;
7. TLS and QUIC both exercise the trust-anchor path;
8. private-key and certificate file paths receive the same ownership audit even though they already use `tokio::fs::read`;
9. repeated cancel/retry cycles do not accumulate unresolved worker operations;
10. unrelated runtime tasks remain responsive during a held credential fixture;
11. shutdown/restart can prove its semantic state: `drained`, `still_draining`, or `contained_by_process_exit`;
12. no regression to raw/base64 credential configuration.

## What not to do

- Do not call a `timeout()` wrapper a cancellation fix unless underlying work is demonstrably terminated or tracked.
- Do not use `spawn_blocking(...).abort()` as proof of cancellation; already-running blocking work cannot generally be assumed to stop just because its async handle was aborted.
- Do not solve the FIFO reproducer by silently special-casing the test while leaving arbitrary blocking credential paths undocumented.
- Do not make DNS behavior incompatible without an explicit resolver/API decision.

## Worldshepherd mapping

This is a SARA/OVERWATCH ownership-and-progress problem rather than ordinary process liveness.

A process may still be alive and the caller may already have timed out, while a native operation remains active and prevents deterministic teardown. Worldshepherd should therefore track at least:

```text
request_state        = CANCELLED
caller_wait_state    = COMPLETE
owned_work_state     = DRAINING | DRAINED | UNKNOWN
containment_state    = IN_PROCESS | PROCESS_EXIT_REQUIRED
```

That separation prevents an audit record from claiming successful cleanup when only the caller's wait ended.

## Ownership / submission boundary

As of the 2026-09-13 / 2026-09-14 UTC audit:

- upstream issue #2784 is open;
- no assignee is shown;
- no issue comments declare ownership;
- no matching implementation PR was found;
- the issue reporter offered standalone redacted fixtures if maintainers identify the preferred test location.

Before any external comment or PR, re-check ownership and Zenoh contribution policy. The next high-value contribution is the regression fixture plus the narrow Phase-1 executor-blocking cleanup, not a broad resolver rewrite without maintainer agreement.
