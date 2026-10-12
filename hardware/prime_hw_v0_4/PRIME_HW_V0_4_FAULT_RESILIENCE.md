# PRIME-HW v0.4 — distance-coded state integrity and bounded fault resilience

**Status:** STACKED DRAFT / IMPLEMENTED / EXACT-HEAD VALIDATION PENDING / BLOCK MERGE

**Dependency:** PRIME-HW v0.3 PR #205 at the branch point. v0.4 is a separate implementation/verification increment and does not change v0.3 evidence retroactively.

## Problem addressed

The PRIME-HW v0.1 reference controller uses seven semantic states represented by ordinary 3-bit binary values `0..6`. That representation is compact, but valid state values exist at Hamming distance 1 from other valid state values. A register-bit corruption can therefore alias another syntactically valid state instead of entering the existing illegal-state/default path.

v0.4 changes the state representation in a new hardened controller while preserving the v0.1 external policy/state semantics under nominal operation.

## Distance-coded state alphabet

The hardened controller uses these exact 8-bit codewords:

| Semantic state | Codeword |
| --- | --- |
| RESET | `0x00` |
| BOOT_LOCKED | `0x0F` |
| VERIFY | `0x33` |
| OPERATIONAL | `0x3C` |
| DEGRADED | `0x55` |
| SAFE | `0x5A` |
| RECOVERY | `0x66` |

The minimum pairwise Hamming distance is **4**. Therefore, under the declared encoded-register bit-flip model, no 1-, 2-, or 3-bit corruption of a valid codeword can become a different valid codeword.

This is a coding-distance property, not a radiation cross-section measurement or a claim that all physical faults appear as clean register-bit flips.

## Fail-closed decoding

`prime_hw_state_code_guard.sv` accepts only the seven exact codewords. Every other 8-bit value is classified invalid and semantically mapped to SAFE.

`prime_hw_policy_controller_hardened.sv` then applies two independent fail-safe effects for invalid encoded state:

1. combinational outputs immediately force `allow=0`, preserve request denial, assert `safe_state`, assert `state_integrity_fault`, and report semantic SAFE; and
2. next-state logic selects the valid encoded SAFE codeword so a subsequent active edge converges the state register into the valid SAFE alphabet.

The integrity output is new in v0.4; it distinguishes an encoded-state integrity failure from an ordinary policy-driven transition into SAFE.

## Verification contract

The v0.4 gate requires all of the following on the exact PR head:

1. **Static code-distance audit** — pairwise minimum Hamming distance must be at least 4.
2. **Exhaustive bounded corruption enumeration** — for every one of the seven valid codewords, every 1-, 2-, and 3-bit corruption is checked for non-aliasing. This is `7 × (C(8,1)+C(8,2)+C(8,3)) = 644` cases.
3. **RTL fault-injection regression** — all 644 corrupted encoded states are forced into the hardened controller without a clock edge; each must assert `state_integrity_fault`, report SAFE, block allow, and deny the active request.
4. **Vendor-neutral synthesis/check** — the hardened controller and guard must elaborate and synthesize through Yosys without structural errors; the generated JSON netlist is preserved as evidence.
5. **Bounded formal safety proof** — the hardened controller must satisfy the declared authorization/fail-safe/transition properties across the recorded symbolic horizon.
6. **Nominal differential miter** — under the same symbolic input history, the hardened controller must match the inherited v0.1 controller for semantic state, `allow`, `deny`, and `safe_state` while no encoded-state corruption is injected.
7. **Guard proof over arbitrary 8-bit values** — an unconstrained symbolic encoded-state probe must be accepted if and only if it is one of the seven declared codewords; every other value must decode invalid and map semantically to SAFE.
8. **Reachability witnesses** — all seven semantic states plus at least one invalid probe code must be reachable in the formal cover run.
9. **Evidence custody** — exact SHA, tool context, model limits, source/test/formal/netlist/log digests, fault-case count, and cover count are preserved in the workflow artifact.

## Explicit fault-model boundary

The intended maximum internal claim after a clean exact-head gate is:

> **PROVEN INTERNALLY IN THE DECLARED RTL/BOUNDED-FORMAL MODEL THAT THE V0.4 DISTANCE-CODED STATE ALPHABET HAS MINIMUM HAMMING DISTANCE 4; ALL 644 ENUMERATED 1-, 2-, AND 3-BIT ENCODED-STATE CORRUPTIONS ARE NON-ALIASING AND FAIL CLOSED IN THE DECLARED RTL INJECTION TEST; AND NOMINAL EXTERNAL POLICY/STATE BEHAVIOR MATCHES THE V0.1 REFERENCE WITHIN THE RECORDED FORMAL HORIZON.**

This does **not** establish:

- unbounded theorem proof;
- complete asynchronous-reset equivalence;
- protection against four-or-more simultaneous state-bit corruptions;
- transient combinational-logic fault coverage;
- clock-tree, reset-tree, CDC, metastability, or timing-fault tolerance;
- memory/interconnect/processor/configuration-memory fault tolerance;
- FPGA configuration-SEU immunity;
- physical fault-injection qualification;
- radiation cross section, LET threshold, TID, SEE, SEL, SEFI, or space qualification;
- ASIC library characterization, PPA closure, DFT, scan-security, or foundry qualification;
- cryptographic root-of-trust assurance; or
- government, avionics, automotive, medical, nuclear, space, or other safety certification.

## Why distance 4 rather than parity-only encoding

A parity bit can detect an odd number of flipped bits but can miss some even-weight corruptions. The selected distance-4 alphabet gives a stronger and directly enumerable semantic-state non-aliasing bound: any corruption of weight 1, 2, or 3 leaves the valid state alphabet.

Distance 4 is not a magic physical-hardening threshold. It is the current logical state-encoding design point, chosen because it materially raises the aliasing barrier while keeping the controller small enough for transparent verification.

## Next promotion gates

After v0.4 passes exact-head CI and independent review, later increments should remain separate and claims-controlled. Candidate next gates are synthesized fault-injection/mutation analysis, temporal fault persistence, duplicated or diverse state observers, clock/reset fault containment, FPGA implementation and timing, and only then device-specific radiation/fault campaigns with a qualified hardware partner.

Keep this PR stacked/draft and **BLOCK MERGE** until exact-head CI is green, evidence is preserved, independent review is clean, and CRE1AWS explicitly authorizes incorporation.
