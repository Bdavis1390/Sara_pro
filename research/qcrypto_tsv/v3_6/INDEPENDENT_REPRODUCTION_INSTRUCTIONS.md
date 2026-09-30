# Independent reproduction instructions — v3.2

Purpose: reproduce the candidate's **software behavior, external Bitcoin-parser enforcement, and candidate-bound external PQ evidence enforcement** without mainnet, real funds, transaction broadcast, or production private keys.

1. Verify the ZIP SHA-256 supplied with the package.
2. Use a reviewer-controlled environment and record OS, Python, OpenSSL, dependency versions, and Bitcoin Core version if used.
3. Run `python -m unittest discover -s tests -v`. Frozen expectation: **132 tests passed, 0 failures**. OpenSSL PQ tests may skip only when the environment lacks the required primitives; record any skip explicitly.
4. Run `python scripts/generate_evidence.py` and confirm source-integrity verification passes.
5. Inspect `evidence/EXTERNAL_PARSER_QUORUM_RECEIPT_V1.json`, `evidence/EXTERNAL_PQ_CANDIDATE_QUORUM_V1.json`, and `evidence/EXTERNAL_PQ_BOUND_PREPARATION_V3_2.json`.
6. Confirm the external parser receipt is bound to the exact PSBT SHA-256, txid and fee.
7. Recompute the v3.2 external PQ candidate challenge and confirm SHA-256 `e8299f29ebf1bc616fe5a1db6ddf415800eea51d2f637e1746f1d73381ed8c96`.
8. Exercise the external PQ evidence gate with: supplied receipt (pass), missing receipt (fail), wrong challenge (fail), wrong signature size (fail), failed tamper control (fail), missing required algorithm (fail), and insufficient family diversity when required (fail).
9. Review implementation paths rather than relying only on tests: PSBT/descriptor guards, operation journals, resource budgets, migration PSBT, source integrity, external parser quorum, external PQ evidence, governed policy binding, PRIME/ECHO/SARA/OVERWATCH, chain context and emergency state.
10. If Bitcoin Core is available, test only REGTEST/SIGNET/TESTNET4. Record binary version and verification method. Do not broadcast.
11. If separately authorized AWS KMS credentials and ML-DSA keys are available, test them only in the reviewer's account and do not expose credentials or key material.
12. Report blocked conditions and disagreements exactly as observed. Do not convert a block or skip into a pass.

Reproduction does not establish Bitcoin BIP activation, mainnet authority, system-level FIPS validation, hardware enclave authenticity, Federal compliance, cryptographic threshold signatures, independent third-party certification, or end-to-end post-quantum Bitcoin consensus security.
