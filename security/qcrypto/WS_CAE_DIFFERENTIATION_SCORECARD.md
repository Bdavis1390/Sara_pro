# WS-CAE Differentiation Scorecard

Status date: 2026-09-13

## Legend

- `YES` — explicitly present in the public scope reviewed.
- `PARTIAL` — adjacent or narrower form is present.
- `NOT IDENTIFIED` — not found in the public scope reviewed; this does not prove absence.
- `N/A` — outside the effort's intended role.

This is a scope-comparison tool, not a quality ranking.

| Effort | Cross-chain heterogeneous account models | Stable authority vs authenticator semantics | Roadmap/testnet/live maturity distinction | Account/vault vs consensus PQ separation | Policy/recovery state in same profile | Evidence/conformance semantics | Independent reproduction target |
|---|---|---|---|---|---|---|---|
| WS-CAE | YES | YES | YES | YES | YES | YES | YES |
| NIST NCCoE Migration to PQC | N/A | NOT IDENTIFIED | PARTIAL | N/A | NOT IDENTIFIED | YES | PARTIAL |
| IETF Crypto-Agility Manifest draft | N/A | NOT IDENTIFIED | PARTIAL | N/A | PARTIAL | YES | YES |
| ISO/TS 23516:2026 | YES, broad DLT interoperability | NOT IDENTIFIED | NOT IDENTIFIED | NOT IDENTIFIED | NOT IDENTIFIED | PARTIAL | PARTIAL |
| ISO/AWI PAS 26347 | YES, wallet interoperability target | NOT IDENTIFIED in public project metadata | NOT IDENTIFIED | NOT IDENTIFIED | NOT IDENTIFIED | NOT IDENTIFIED | NOT IDENTIFIED |
| PQMigrate | YES, chain-agnostic wallet/light-client migration | PARTIAL | YES, phased policy modes | YES, preserves later consensus migration boundary | PARTIAL | PARTIAL | Research evaluation |
| BGIN PQC Migration | YES, DLT stacks/wallets/operators | PARTIAL | YES, staged migration focus | PARTIAL | PARTIAL | YES, neutral evaluation direction | Multi-stakeholder process |
| Project Eleven libqc / Quantum Vault | PARTIAL, Ethereum plus Bitcoin support | YES in crypto-agile wallet/account design | PARTIAL | PARTIAL | YES | YES, audited implementation | YES, open-source implementation |
| Q-Sign | N/A for blockchain account models | YES, authority/delegation substrate | PARTIAL | N/A | YES | YES, conformance contract | YES |
| LayerQu | YES, 72-chain measurement | PARTIAL, evaluates key rotation/account model | YES | YES | PARTIAL | YES, public methodology | YES, independent scoring methodology |
| Algorand native rekey/PQ accounts | Single chain | YES | YES | YES | PARTIAL | Chain-native evidence | N/A |
| Ethereum EIP-8141 | Single chain | YES | YES | YES, broader PQ roadmap is separate | YES through programmable validation | Protocol specification/review | N/A |
| Sui aliases/PQ roadmap | Single chain | YES | YES | YES | YES, vault/account distinction | Public roadmap and implementation evidence | N/A |
| Shell native PQ AA | Single chain | YES | YES | PARTIAL | YES | Public implementation/test evidence | N/A |

## Apparent gap

The surrounding ecosystem already supplies strong components: algorithms, interoperability testing, migration blueprints, wallet implementations, readiness scoring, authority substrates, and chain-native account abstraction.

The gap visible in this scorecard is the combination of all of the following in one profile:

1. heterogeneous blockchain account models;
2. stable-authority/authenticator separation;
3. explicit deployment-maturity state;
4. explicit account-vs-consensus PQ claims boundary;
5. policy/recovery state;
6. evidence/conformance semantics;
7. a direct independent-reproduction challenge.

That combination is the WS-CAE research lead under test.

## Falsification rule

If a public artifact is identified that already combines these properties for heterogeneous blockchain account models, this scorecard must be updated and the spearhead claim narrowed or withdrawn.

No certification, standards-body adoption, production approval, or global novelty claim is implied.
