# Worldshepherd QCRYPTO — Production Assurance Status

**Public status date:** 2026-09-17  
**Publication class:** Public technical status / claims-control record  
**Overall state:** **PRODUCTION_ASSURANCE_PROGRESS_NOT_PRODUCTION_CERTIFICATION**

Worldshepherd QCRYPTO now contains a production-oriented opaque-signing architecture, an AWS KMS ML-DSA-65 provider adapter, a protected live-integration workflow, separate production-assurance and native-execution evidence guards, and exact claim barriers for FIPS, Federal, independent-validation, blockchain-native, mainnet, real-value, and end-to-end post-quantum assertions.

This page publishes what is actually established and what remains evidence-gated.

## 1. Production HSM/KMS integration

**Current state:** `PROVIDER_ADAPTER_IMPLEMENTED_LIVE_PROBE_AVAILABLE_LIVE_OBSERVATION_NOT_ESTABLISHED`

Implemented:

- AWS KMS `ML_DSA_65` / `SIGN_VERIFY` opaque-provider adapter.
- FIPS 204 context preservation through AWS KMS `EXTERNAL_MU`.
- Provider-side AWS KMS `Verify` plus independent local verification.
- GitHub OIDC short-lived AWS credentials; no static AWS access key is accepted by the live workflow.
- Protected GitHub environment boundary for the designated KMS key.
- AWS FIPS endpoint required by the live probe.
- AWS SDK `total_max_attempts=1` so an ambiguous non-idempotent `Sign` request is not automatically retransmitted by the SDK.
- Automatic Worldshepherd retry of an ambiguous KMS signing outcome remains forbidden.

Not yet established:

- A successful protected live AWS KMS probe artifact against a configured production AWS account/key.

A live PASS may promote only the HSM/KMS integration axis to `LIVE_HSM_KMS_INTEGRATION_OBSERVED`; it does not automatically promote any other claim.

## 2. FIPS status

**Current state:** `ACTIVE_PROVIDER_CERTIFICATE_FOUND_MLDSA_SCOPE_NOT_INDEPENDENTLY_VERIFIED`

NIST FIPS 204 is the final ML-DSA standard. AWS currently documents its ML-DSA KMS keys and signing operations as being protected by FIPS 140-3 Security Level 3 validated HSMs.

Separately, the NIST CMVP database currently shows AWS Key Management Service HSM certificate **#4884** as **Active**, FIPS 140-3, Level 3, with a sunset date of **2026-11-17**. The certificate's published approved-algorithm list, however, does not list ML-DSA. NIST's current Implementation Under Test list also contains newer AWS KMS HSM versions.

Therefore Worldshepherd currently records:

- provider vendor FIPS statement: **supported by AWS documentation**;
- active AWS KMS HSM CMVP certificate: **independently located**;
- independently verified CMVP scope covering the ML-DSA operation used here: **not established**;
- Worldshepherd CMVP validation: **not established**.

Worldshepherd will not convert use of a validated provider module into a claim that the Worldshepherd application itself is FIPS validated. NIST explicitly distinguishes a validated cryptographic module from a larger product/application that merely uses one.

## 3. Bitcoin / Ethereum native execution

**Current state:** `NATIVE_EXECUTION_NOT_ESTABLISHED`

The repository contains admission logic that keeps the following evidence states independent:

1. verified chain-native signature;
2. verified broadcast receipt and canonical transaction identifier;
3. distinct mainnet authorization;
4. independently verified real-value execution receipt.

None of those production claims is currently asserted.

Worldshepherd governance still cannot self-grant execution, private-key-operation, broadcast, mainnet, or real-value authority. The production-assurance guard now additionally requires exact evidence-digest binding before admitting a Bitcoin or Ethereum native-signature claim, verified transaction identity before broadcast, verified authority issuer before mainnet authority, and independent receipt verification before any real-value movement claim.

## 4. Federal status

**Current state:** `FEDERAL_REQUIREMENT_MAPPING_NOT_FEDERAL_COMPLIANCE`

Executive Order 14412 and OMB M-26-15 materially strengthen the Federal PQC migration requirement. They do not themselves constitute an assessment or certification of Worldshepherd.

Worldshepherd may publish requirement traceability, migration readiness, CBOM/provenance controls, policy enforcement, evidence custody, and internal reproducibility. A Federal compliance claim remains blocked unless evidence is simultaneously:

- attributable to the relevant assessment;
- bound to the exact scope and version assessed;
- associated with a verified assessor/authority;
- complete for the applicable control set.

No such complete attributable Federal assessment is currently recorded.

## 5. Independent validation

**Current state:** `EXTERNAL_INDEPENDENT_REPRODUCTION_REQUIRED`

Internal CI, deterministic artifacts, and reproducible repository workflows are not independent validation.

The production-assurance guard now requires all three before admitting an independent-validation claim:

- an external reproduction record;
- verified independent reviewer identity;
- binding to the exact reviewed artifact digest.

No complete third-party reproduction record meeting those requirements is currently present.

## 6. End-to-end post-quantum cryptocurrency security

**Current state:** `SYSTEM_WIDE_PQ_SECURITY_NOT_ESTABLISHED`

An ML-DSA custody or application signature is not equivalent to end-to-end quantum resistance of a cryptocurrency system.

As of this publication:

- Bitcoin BIP-360 (Pay-to-Merkle-Root / P2MR) is **Draft**.
- Bitcoin BIP-361 (Post Quantum Migration and Legacy Signature Sunset) is **Draft**.
- The Ethereum Foundation states a target of **December 2029** for Ethereum L1 quantum resistance across execution, consensus, and data.

Worldshepherd therefore requires production evidence across transaction authority, consensus, data availability, bridge/custody, network transport, deployed production behavior, and independent validation before an end-to-end PQ cryptocurrency-security claim can be admitted.

That evidence is not currently complete.

## 7. Evidence hierarchy

The currently defensible hierarchy is:

`IMPLEMENTED_IN_SOFTWARE`

→ `PROVEN_INTERNALLY` only after exact-head CI passes

→ `LIVE_PROVIDER_INTEGRATION_OBSERVED` only after the protected AWS live probe passes

→ provider FIPS scope only when the exact module/version/algorithm/service is independently tied to active CMVP evidence

→ `INDEPENDENTLY_REPRODUCED` only with an external identity- and artifact-bound reproduction record

→ Federal, native-mainnet, real-value, or end-to-end PQ claims only when their own independent evidence gates are satisfied.

No evidence class automatically promotes another.

## 8. Official references

- NIST FIPS 204: https://csrc.nist.gov/pubs/fips/204/final
- AWS KMS ML-DSA: https://docs.aws.amazon.com/kms/latest/developerguide/mldsa.html
- NIST CMVP certificate #4884: https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/4884
- NIST CMVP Implementation Under Test list: https://csrc.nist.gov/projects/cryptographic-module-validation-program/modules-in-process/IUT-List
- NIST CMVP validated-module guidance: https://csrc.nist.gov/Projects/cryptographic-module-validation-program/validated-modules
- Executive Order 14412: https://www.whitehouse.gov/presidential-actions/2026/06/securing-the-nation-against-advanced-cryptographic-attacks/
- OMB M-26-15: https://www.whitehouse.gov/wp-content/uploads/2026/06/M-26-15-Execution-of-the-Migration-to-Post-Quantum-Cryptography.pdf
- Bitcoin BIPs repository: https://github.com/bitcoin/bips
- Ethereum Foundation protocol priorities, 2026-09-07: https://blog.ethereum.org/2026/09/07/protocol-priorities

## Claims boundary

This publication documents current implementation and evidence state. It does **not** assert that Worldshepherd is FIPS validated, Federal compliant, independently validated, authorized for mainnet or real-value execution, or end-to-end post-quantum secure for Bitcoin or Ethereum. It does not report a real-value transaction or authorize one.
