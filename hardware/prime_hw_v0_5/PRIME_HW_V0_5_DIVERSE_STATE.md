# PRIME-HW v0.5 — representation-diverse state integrity monitor

**Status:** STACKED DRAFT / IMPLEMENTED / EXACT-HEAD VALIDATION PENDING / BLOCK MERGE

**Dependency:** PRIME-HW v0.4 PR #237. v0.5 is a separate implementation and verification increment; it does not rewrite or upgrade v0.4 evidence retroactively.

## Problem addressed

PRIME-HW v0.4 raises the encoded-state aliasing barrier by using seven 8-bit state codewords with minimum pairwise Hamming distance 4. Under its declared state-register bit-flip model, every 1-, 2-, or 3-bit corruption leaves the valid primary-state alphabet and therefore fails closed.

That bound is intentionally finite. A corruption of four or more primary state bits can, for some masks, transform one valid 8-bit codeword into another valid 8-bit codeword. A single representation cannot distinguish that valid-code alias from a legitimate state transition solely by codeword validity.

v0.5 adds a second, independently stored **representation-diverse shadow state** so authorization depends on agreement between two different state encodings.

## Dual state representations

### Primary state domain

The v0.4 8-bit distance-coded alphabet is retained:

| Semantic state | Primary code |
| --- | --- |
| RESET | `0x00` |
| BOOT_LOCKED | `0x0F` |
| VERIFY | `0x33` |
| OPERATIONAL | `0x3C` |
| DEGRADED | `0x55` |
| SAFE | `0x5A` |
| RECOVERY | `0x66` |

### Shadow state domain

The new shadow state is stored independently as a 7-bit one-hot code:

| Semantic state | Shadow code |
| --- | --- |
| RESET | `0000001` |
| BOOT_LOCKED | `0000010` |
| VERIFY | `0000100` |
| OPERATIONAL | `0001000` |
| DEGRADED | `0010000` |
| SAFE | `0100000` |
| RECOVERY | `1000000` |

The primary and shadow transition paths are written separately in RTL. Both consume the same policy inputs, but they use different stored representations and independently encoded transition assignments.

## Integrity rule

`prime_hw_dual_state_guard.sv` accepts a controller state only when:

1. the primary 8-bit value is one of the seven exact primary codewords;
2. the shadow 7-bit value is one of the seven exact one-hot codewords; and
3. both representations decode to the same semantic state.

Any violation asserts `state_integrity_fault`. While the fault is asserted, the controller immediately:

- forces `allow=0`;
- preserves denial of an active request;
- reports semantic SAFE;
- asserts `safe_state`; and
- selects the valid SAFE representation in both state domains for the next active edge.

This means a corruption that aliases another valid primary codeword is still detected when the uncorrupted shadow remains at the original semantic state. The reverse is also true for an isolated shadow-domain alias.

## Complete encoded-pair contract

The combined state representation has `2^8 × 2^7 = 32,768` possible primary/shadow encoded pairs.

Exactly seven pairs are accepted: the seven matching semantic-state pairs. The remaining **32,761 pairs** must assert integrity fault in the declared combinational guard model.

The formal harness uses unconstrained 8-bit and 7-bit symbolic probes to prove that complete acceptance-set contract rather than sampling a subset of pairs.

## Exhaustive isolated-domain mutation campaigns

From each of the seven valid matched pairs, CI enumerates every nonzero arbitrary mask isolated to one state-storage domain at a time:

- primary: `7 × 255 = 1,785` mutations;
- shadow: `7 × 127 = 889` mutations;
- total: **2,674 isolated arbitrary state-domain mutations**.

The mask weight is unrestricted. These campaigns therefore include single-bit faults, multi-bit invalid patterns, and valid-code alias transitions in the corrupted domain.

Every injected mutation must assert `state_integrity_fault`, report semantic SAFE, block `allow`, and deny the active request.

## Vendor-neutral structural evidence

The v0.5 Yosys evidence path preserves and audits both stored state nets after flattening/elaboration:

- `primary_state_q`: 8 bits;
- `shadow_state_q`: 7 bits;
- bit sets must be disjoint;
- all 15 bits must remain driven by sequential cells.

The RTL applies `keep` attributes to the two state-store nets so the evidence netlist remains auditable.

This structural check proves only what exists in the generated Yosys evidence netlist. It does **not** prove physical separation, placement diversity, routing independence, clock-tree independence, power-domain independence, or resistance to common-mode silicon faults.

## Nominal semantic equivalence

A bounded formal differential miter drives the v0.5 controller and inherited v0.1 controller with the same symbolic policy/input history. On the nominal synchronized path, v0.5 must match v0.1 for:

- semantic `state_code`;
- `allow`;
- `deny`; and
- `safe_state`.

The integrity monitor is therefore intended to add state-representation fault detection without silently changing nominal policy semantics.

## Exact-head verification contract

The v0.5 CI gate requires all of the following on one exact PR head:

1. complete static enumeration of all 32,768 encoded pairs, accepting exactly seven and faulting 32,761;
2. exhaustive 2,674-case isolated-domain RTL mutation campaign;
3. vendor-neutral Yosys synthesis/check;
4. post-elaboration structural audit showing 8-bit primary and 7-bit shadow state nets remain disjoint and sequentially stored;
5. 40-step bounded formal safety and nominal-equivalence proof;
6. complete symbolic dual-guard acceptance-set proof across the full 15-bit pair space;
7. ten formal cover witnesses: seven nominal semantic states plus invalid-primary, invalid-shadow, and valid-but-mismatched fault classes; and
8. exact-SHA evidence custody with source, netlist, SMT model, and result hashes.

## Claims boundary

If all exact-head gates pass, the maximum intended internal machine-supported claim is:

> **PROVEN INTERNALLY IN THE DECLARED RTL/YOSYS-STRUCTURAL/BOUNDED-FORMAL MODEL THAT THE V0.5 DUAL-REPRESENTATION GUARD ACCEPTS ONLY THE SEVEN EXACT MATCHED PRIMARY/SHADOW STATE PAIRS; ALL 32,761 OTHER ENCODED PAIRS ASSERT INTEGRITY FAULT IN THE DECLARED GUARD MODEL; ALL 2,674 ENUMERATED ARBITRARY NONZERO STATE-BIT MUTATIONS ISOLATED TO EITHER PRIMARY OR SHADOW STORAGE FAIL CLOSED IN THE DECLARED RTL REGRESSION; BOTH STATE STORES REMAIN DISTINCT 8-BIT AND 7-BIT SEQUENTIAL NETS IN THE RECORDED YOSYS EVIDENCE NETLIST; AND NOMINAL EXTERNAL POLICY/STATE BEHAVIOR MATCHES THE V0.1 REFERENCE WITHIN THE RECORDED 40-STEP FORMAL HORIZON.**

This does **not** establish:

- simultaneous corruption of both representations;
- common-mode transition-logic, input, clock, reset, power, or synthesis faults;
- physical independence or physical placement separation;
- protection against an adversarial or correlated fault that changes both domains to the same semantic state;
- transient-glitch, CDC, metastability, or physical timing tolerance;
- FPGA configuration-memory fault immunity;
- radiation SEE/SEU/SEL/SEFI/TID qualification;
- fault cross-section or LET thresholds;
- ASIC PPA, DFT, scan-security, or foundry qualification;
- cryptographic root-of-trust assurance; or
- government, aerospace, automotive, medical, nuclear, space, or other safety/security certification.

The formal SMT path lowers asynchronous resets with `async2sync; dffunmap`; that transformation is part of the formal-model boundary and is not a separate asynchronous-reset-equivalence proof.

## Next promotion gates

After v0.5 exact-head CI and independent review, the next substantial assurance increment should leave source-level state injection and move toward **post-synthesis mutation analysis**: mutate synthesized next-state/guard logic and authorization-control nodes, classify detected versus undetected faults, and use the residual escapes to drive selective logic duplication or diverse checking. Physical placement, clock/reset independence, FPGA implementation, and radiation/fault campaigns remain later partner/device-specific gates.

Keep this PR stacked/draft and **BLOCK MERGE** until exact-head CI is green, evidence is preserved, independent review is clean, the dependency stack is reconciled, and CRE1AWS explicitly authorizes incorporation.
