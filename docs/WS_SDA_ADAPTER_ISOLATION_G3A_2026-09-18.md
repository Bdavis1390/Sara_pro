# WS-SDA G3 — Adapter Resource + Container Isolation Baseline

Status: **G3A + G3B IMPLEMENTED IN SOFTWARE ON STACKED BRANCH — EXACT-HEAD CI NOT YET EXECUTED**
Date: 2026-09-18
Branch: `feature/ws-sda-adapter-isolation-g3a-20260918`
Parent gate: WS-SDA G1/G2 PR #447

## 1. Objective

G3 separates untrusted source material from the SARA/SDA trust core. G3A implements
a bounded local subprocess execution boundary for configured source adapters.

The security model is intentionally asymmetric:

- the adapter executable and its arguments are trusted configuration;
- the source payload is untrusted;
- the adapter receives no inherited Worldshepherd secret environment;
- the adapter receives an ephemeral working directory;
- shell interpretation is disabled;
- file descriptors are closed rather than inherited;
- the adapter runs in a separate process session;
- input, output, stderr, CPU, memory, open-file and wall-clock limits are explicit.

## 2. Implemented controls

`worldshepherd_sara/sda_adapter_isolation.py` applies:

1. absolute executable-path requirement;
2. `shell=False` and bounded argument count/length;
3. pre-execution input-byte quota;
4. minimal child environment containing only locale and Python hardening variables;
5. mode-0700 ephemeral working directory;
6. stdin from a private bounded file descriptor;
7. regular-file stdout/stderr capture rather than unbounded parent memory buffering;
8. POSIX `RLIMIT_CORE=0`;
9. `RLIMIT_CPU`;
10. `RLIMIT_AS`;
11. `RLIMIT_NOFILE`;
12. `RLIMIT_FSIZE`;
13. wall-clock timeout followed by process-group kill;
14. bounded stdout/stderr readback;
15. explicit allowed-exit-code policy;
16. fail-closed result classification.

## 3. G3A executable tests

The test candidate proves:

- oversized input is rejected before process execution;
- a parent secret environment variable is absent in the adapter;
- the working directory is ephemeral;
- shell metacharacters remain literal arguments rather than executing a shell;
- wall-clock timeout kills the adapter process group;
- stdout and stderr floods are bounded;
- a non-allowed exit code fails closed;
- a missing configured executable fails before execution;
- NUL and argument-count violations fail closed.

## 4. Security boundary

G3A materially reduces adapter blast radius, but it is **not** a complete hostile-code
sandbox.

It does **not** yet establish:

- network namespace isolation or deny-by-default egress;
- filesystem root isolation/chroot/pivot_root;
- seccomp syscall filtering;
- AppArmor/SELinux confinement;
- container/microVM escape resistance;
- executable-signature or artifact-digest pinning;
- production secrets broker integration;
- production certificate/PKI governance;
- independent penetration testing;
- government/customer accreditation.

Accordingly the result field exposes `network_isolation_enforced = false`. That is
an intentional evidence property, not an implementation detail to conceal.

## 5. G3B container/network/filesystem boundary implemented

The stacked branch now adds `scripts/sda_adapter_container_isolation_drill.sh` and a
dedicated `WS-SDA Adapter Isolation G3` CI workflow. The drill builds the exact tested
SARA image and executes an adapter probe with:

- `--network none`;
- read-only root filesystem;
- writable `/tmp` only as bounded tmpfs scratch;
- `no-new-privileges`;
- all Linux capabilities dropped;
- fixed non-root UID/GID;
- PID, memory and CPU limits;
- no host port bindings;
- no host mounts;
- no inherited test secret;
- exact-source-commit image-label verification.

The runtime probe additionally demonstrates that external network connection fails,
the root filesystem is not writable, tmpfs scratch is writable, and only loopback is
visible in the reference network namespace.

The reference architecture is therefore:

```text
untrusted source
    |
    v
bounded intake queue
    |
    v
ephemeral adapter container / namespace
    |-- read-only root filesystem
    |-- no inherited secrets
    |-- drop all capabilities
    |-- no-new-privileges
    |-- non-root UID
    |-- explicit memory/CPU/pid/file limits
    |-- deny-by-default network
    |-- writable tmpfs scratch only
    v
bounded canonical output
    |
    v
schema + identity + provenance verification
    |
    +--> ACCEPT
    +--> QUARANTINE
    +--> REJECT
```

This deliberately reuses the repository’s Docker/read-only/cap-drop/no-new-privileges
patterns from the SARA TLS/private-backend and Verified Local work rather than
inventing a second isolation model.

G3 is still a **candidate** until both G3A and G3B exact-head CI pass. Even after that,
the correct claim is reference software/container isolation, not protection against
all hostile code or container/runtime/kernel compromise.

## 6. Claims block

```yaml
claim:
  statement: "Worldshepherd implements bounded SDA adapter subprocess controls plus a deny-network, read-only, non-root container reference boundary with explicit resource and secret-isolation evidence."
  status:
    - IMPLEMENTED_IN_SOFTWARE
  evidence:
    - deployments/sara_verified_local_v1/worldshepherd_sara/sda_adapter_isolation.py
    - deployments/sara_verified_local_v1/tests/test_sda_adapter_isolation.py
    - deployments/sara_verified_local_v1/scripts/sda_adapter_container_isolation_drill.sh
    - .github/workflows/ws-sda-adapter-isolation-g3.yml
  limitations:
    - "G3A alone does not enforce network isolation; G3B uses Docker network=none."
    - "No VM/microVM isolation or custom seccomp/AppArmor/SELinux claim."
    - "No guarantee against Docker/runtime/kernel escape."
    - "No hostile-code universal sandbox or accreditation claim."
  next_gate: "Pass exact-head G3A/G3B CI, then add adversarial escape/containment corpus and artifact-identity controls without weakening G1/G2."
```
