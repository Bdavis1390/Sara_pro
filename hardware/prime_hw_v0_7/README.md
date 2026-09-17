# PRIME-HW v0.7 — Temporal Command Integrity / Anti-Replay Execution Gate

## Status

**IMPLEMENTED / EXACT-HEAD VALIDATION PENDING / INDEPENDENT REVIEW PENDING / BLOCK MERGE**

v0.7 is stacked on the exact machine-green PRIME-HW v0.6 authorization-integrity head. It does not replace the v0.6 policy decision. It adds a separate execution-authorization boundary so a correct policy `allow` cannot be silently reused as a stale, duplicate, or out-of-order actuation event.

## Architecture

The v0.7 execution path separates two meanings:

- `policy_allow`: the inherited v0.6 answer to whether the current request is policy-authorized.
- `execute_pulse`: a one-transaction execution authorization that additionally requires temporal identity integrity.

The temporal guard stores an 8-bit expected command sequence in two logical representations:

- `expected_seq_q` — primary sequence value;
- `expected_seq_inv_q` — independently stored bitwise complement.

Only complementary primary/inverse pairs are accepted as valid sequence state. The complete pair space is 65,536 combinations: exactly 256 complementary pairs are valid and 65,280 are invalid.

An execution pulse requires all of the following in the declared synchronous RTL model:

1. upstream v0.6 policy authorization;
2. an active request;
3. valid complementary sequence storage;
4. `command_seq == expected_seq_q`;
5. no previously latched temporal fault.

A successful execution advances the expected sequence by exactly one modulo 256 and updates the inverse store to the exact complement. Unauthorized traffic does not execute, advance the sequence, or create a sequence-mismatch fault.

## Fail-closed behavior

The guard immediately blocks execution and asserts a temporal integrity fault when:

- the stored primary/inverse sequence pair is inconsistent; or
- an upstream-approved active request presents a command sequence other than the currently expected value.

The fault is sticky until reset. The wrapper feeds the latched temporal fault into the inherited v0.6 fatal path, while the temporal guard itself blocks execution immediately. This creates a two-stage response: immediate actuation denial followed by semantic convergence toward SAFE.

## Declared verification contract

Exact-head CI is required to establish on one immutable SHA:

- complete enumeration of all **65,536** primary/inverse sequence-state pairs, accepting exactly **256** complementary pairs and rejecting **65,280**;
- nominal in-order exactly-once progression;
- unauthorized-mismatch no-poison behavior;
- future/out-of-order approved-command rejection;
- stale replay rejection;
- held-request duplicate rejection after the first acceptance;
- one complete modulo-256 epoch including `0xff -> 0x00` wrap and post-wrap execution;
- live isolated corruption of both primary and inverse sequence stores;
- vendor-neutral Yosys synthesis/check;
- synthesized evidence of 8+8 disjoint, sequentially driven preserved sequence-state bits and the sticky temporal-fault latch;
- synthesized execution-cone dependency on both stored sequence representations, sticky fault state, upstream authorization, request-valid, and all command-sequence bits;
- top-level integration showing that `execute_pulse` is the temporal guard output and that the temporal latch structurally feeds the SAFE-state cone;
- a **60-step** bounded formal safety and nominal-equivalence proof against exact v0.6 under the declared conforming in-order protocol;
- complete symbolic complementary-pair contract and unconstrained temporal-guard safety properties;
- **13/13** formal reachability/fault witnesses; and
- exact-SHA source/netlist/SMT/result hashes in the evidence artifact.

## Claims boundary

Even after a fully green gate, v0.7 does **not** establish:

- cryptographic command authenticity or integrity;
- protection against an attacker who can generate the currently expected command sequence;
- replay protection across reset, power loss, or a new session/epoch;
- uniqueness beyond the finite 8-bit modulo sequence space;
- nonvolatile anti-rollback state;
- transport/network ordering guarantees outside this synchronous interface;
- CDC, metastability, asynchronous-glitch, clock, reset, or power-fault tolerance;
- physical independence of the two sequence stores;
- FPGA configuration-memory upset immunity or radiation qualification;
- physical actuator feedback or proof that an actuator obeyed `execute_pulse` exactly once;
- ASIC PPA/timing/DFT/foundry qualification; or
- certification.

The 8-bit sequence width is intentionally a verification demonstrator, not a production anti-replay epoch size. A deployable protocol should bind a much larger monotonic transaction identifier to an authenticated session/epoch and retained anti-rollback state appropriate to the threat model.
