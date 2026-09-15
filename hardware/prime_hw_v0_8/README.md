# PRIME-HW v0.8 — Session/Epoch-Bound Authenticated Command Envelope

## Status

**PROVISIONAL STACKED IMPLEMENTATION / INHERITS V0.7 VALIDATION BLOCKER / EXACT-HEAD VALIDATION PENDING / INDEPENDENT REVIEW PENDING / BLOCK MERGE**

v0.8 is stacked on the frozen v0.7 temporal-command head while v0.7 exact-head CI is pending. v0.8 cannot be promoted beyond its inherited base evidence. If v0.7 changes, this branch must be reconciled and revalidated.

## Security/control objective

v0.7 prevents stale, duplicate, and out-of-order execution within a declared synchronous transaction epoch. v0.8 addresses a different class of hazard: the command presented for execution must be the exact epoch/sequence/digest tuple that an external verifier authenticated, and the command epoch must equal the current trusted epoch supplied by an external monotonic root.

The ordering is intentional:

`v0.6 policy authorization -> v0.8 authenticated-envelope binding -> v0.7 temporal sequence gate -> execute_pulse`

An authentication mismatch therefore cannot consume or advance v0.7 temporal sequence state.

## Trust contract

v0.8 consumes two external trust sources:

1. `trusted_epoch_valid` + `trusted_epoch[31:0]`: the current epoch supplied by a trusted monotonic/rollback-resistant root.
2. `verifier_valid` + `verified_epoch/verified_seq/verified_command_digest`: the tuple asserted by an external cryptographic verifier to have passed authentication.

**v0.8 does not implement or prove either external trust source.** It proves only the hardware enforcement and binding logic conditioned on those inputs being truthful.

The live command tuple is:

- `command_epoch[31:0]`
- `command_seq[7:0]`
- `command_digest[63:0]`

The envelope is binding-valid only when:

- the trusted epoch source is valid;
- the verifier result is valid;
- live command epoch equals trusted epoch;
- verifier epoch equals live command epoch;
- verifier sequence equals live command sequence; and
- verifier digest equals live command digest.

A policy-approved active request without this exact binding is denied and raises a sticky authentication-integrity fault. The latched authentication fault feeds the inherited fatal path for semantic SAFE convergence. A valid authenticated admission then enters the exact v0.7 temporal gate; only the temporal gate can produce `execute_pulse`.

## Verification contract

Exact-head CI must establish on one immutable SHA:

- **512/512** abstract envelope-control/mismatch cases across five Boolean control conditions and four independently perturbed binding dimensions;
- sticky authentication-fault capture and reset behavior;
- complete symbolic equality proof over unconstrained 32-bit epoch, 8-bit sequence, and 64-bit digest values;
- vendor-neutral Yosys synthesis/check;
- post-synthesis evidence that authenticated admission depends on every declared external trust/live tuple input plus sticky authentication state;
- post-synthesis evidence that authentication-integrity-fault and envelope-binding cones contain the full declared verifier/live tuple;
- post-synthesis evidence that the authentication fault latch remains sequential;
- top-level structural evidence that v0.7 temporal admission is driven only by the preserved authenticated-allow rail and directly drives `execute_pulse`;
- structural SAFE-state escalation from both authentication and temporal sticky faults;
- **70-step** bounded formal proof that a valid external trust contract preserves exact v0.7 policy/state/temporal/execution behavior while the independent envelope probe satisfies the complete symbolic guard contract;
- **16/16** formal semantic/authentication witness covers; and
- exact-SHA source/netlist/SMT/result hashes.

## Conditional cross-reset anti-replay statement

If—and only if—the external trusted epoch is monotonic and rollback-resistant across reset/power/session boundaries, and the external verifier authenticates the exact epoch/sequence/digest tuple, replay of a command from an older epoch is rejected because its live/verified epoch cannot equal the current trusted epoch.

That is a **conditional enforcement property**, not an internal proof of cross-reset anti-replay. This RTL contains no nonvolatile monotonic counter, secure element, TPM, PUF, cryptographic key store, or MAC/signature verifier.

## Claims boundary

Even after a fully green v0.8 gate, no claim is made for:

- cryptographic algorithm correctness or strength;
- key generation, storage, rotation, revocation, zeroization, or compromise resistance;
- authenticity of `verifier_valid` or the verified tuple;
- monotonicity, nonrollback, retention, or authenticity of `trusted_epoch`;
- resistance to a malicious or compromised verifier/root that asserts false values;
- collision resistance or preimage resistance of the externally supplied command digest;
- replay protection if the trusted epoch rolls back or repeats;
- nonvolatile temporal sequence retention;
- network ordering, transport security, CDC, metastability, asynchronous glitches, clock/reset/power faults;
- physical independence, side-channel/fault-injection resistance, FPGA configuration-memory/radiation immunity;
- physical actuator exactly-once behavior; or
- ASIC timing/PPA/DFT/foundry qualification or certification.

The present widths are verification-demonstrator parameters. A deployable design should choose epoch/counter/digest sizes and cryptographic primitives from the system threat model and approved security architecture rather than inheriting these proof-sized constants mechanically.
