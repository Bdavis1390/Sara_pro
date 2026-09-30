# Independent reproduction instructions — QCRYPTO + TSV v3.4

Purpose: reproduce the **software controls, lineage validation, and hosted-execution evidence checks** without live tokenized-equity trading, production custody, real funds, or a claim of SEC/legal compliance.

1. Verify the frozen v3.4 ZIP SHA-256 published with the release.
2. Record the reviewer-controlled OS, Python, OpenSSL, dependency versions, and clock source.
3. Run `python -m unittest discover -s tests -v`. Frozen expectation for this source tree: **221 PASS / 0 FAIL**.
4. Run `python scripts/generate_tsv_v3_4_evidence.py`.
5. Confirm source integrity is satisfied and record `SOURCE_INTEGRITY_MANIFEST_V3_4.json`.
6. Validate `evidence/TSV_EXTERNAL_EXECUTION_BUNDLE_V3_4.json` with `tsv.external_execution.validate_external_tsv_execution_bundle()`.
7. Confirm the bundle is bound to v3.3 release SHA-256 `fab44ddd5a1d46516f8d2b9fc759f4f23db7d811ab8a7d7a9b79da2d0400a25f` and v3.3 source-manifest SHA-256 `36af6e42fb78ab6e97a56678b87afc02ff71d4ea79d3d11a778eb03a31c9becc`.
8. Confirm hosted positive receipt SHA-256 `7ef9a0174fe3f429489d258228dc91ca8475a9db7cb43434469aebdd4ec85137`.
9. Confirm all six named negative cases are present and DENY the intended gate.
10. Mutate one byte/field in the external bundle without recomputing its bundle hash; validation must DENY with `BUNDLE_HASH_MISMATCH`.
11. Inspect `evidence/EXTERNAL_FUNCTION_METADATA_V3_4.json`. JWT verification must be true.
12. Inspect `evidence/TSV_QCRYPTO_BINDING_V3_4.json`; the external TSV execution bundle hash must be committed into the binding.
13. Treat the weekends-only external business-day calculation as a reproducibility aid only. Supply/validate an authoritative calendar before any operational use.
14. Report blocks, skips, source mismatches, or disagreements exactly as observed. Do not promote them to PASS.

Reproduction does not establish SEC approval, legal compliance, registration, market-data licensing, live venue operation, clearing/settlement authority, custody fitness, Federal compliance, or independent certification.
