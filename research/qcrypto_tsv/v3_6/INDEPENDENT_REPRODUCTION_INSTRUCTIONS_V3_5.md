# Independent reproduction instructions — v3.5

Purpose: independently reproduce the v3.5 **software behavior and evidence validation** without live securities trading, real funds, production private keys, licensed-feed impersonation, or any assertion of SEC/legal compliance.

1. Verify the release ZIP SHA-256 and the supplied sidecar before extraction.
2. Record reviewer-controlled OS, Python, OpenSSL, dependency versions, and UTC time source.
3. Run `python -m unittest discover -s tests -v`. Expected source-tree/frozen target: **268 PASS / 0 FAIL**.
4. Run `python scripts/generate_tsv_v3_5_evidence.py` and require exit code 0.
5. Verify `SOURCE_INTEGRITY_MANIFEST_V3_5.json` and `evidence/SOURCE_INTEGRITY_REPORT_V3_5.json` report the same current source manifest.
6. Inspect `evidence/TSV_EXTERNAL_ADVERSARIAL_BUNDLE_V3_5.json`. Confirm exact parent v3.4 hash, v3.5 control-core hash, Supabase function identity/version, JWT=true, positive receipt, and all 11 named negative cases.
7. Re-run the local external-bundle validator tests and mutate at least one receipt/case to confirm fail-closed bundle-hash behavior.
8. Exercise `market_data_adapter.py` with: stale message, future skew, delay excess, duplicate, replay, sequence gap, equivocation, conflicting status, primary halt, LULD pause, missing primary source, incomplete resume quorum, and valid ordered two-source stream.
9. Exercise `issuer_delivery.py` with: valid receipt, absent receipt, wrong Notice digest, bad provider/channel, timestamp reversal, provider delay, <30-day wait, issuer objection, and future objection.
10. Confirm `authorize_operational_tsv()` can require both adapter classes and forces `DENY` when either class fails.
11. Verify `evidence/TSV_QCRYPTO_BINDING_V3_5.json` commits to the exact v3.5 external adversarial bundle and control-core hashes.
12. Treat all external market-source IDs and issuer-provider identities in the bundled reproducer as synthetic. Do not describe them as live SIP/exchange/LULD/provider connections.
13. Report skips, environment limitations, disagreements, or failed controls exactly as observed. Never promote a blocked, skipped, synthetic, or failed condition into a PASS.

Reproduction does **not** establish SEC approval, legal compliance, registration, licensed market-data access, qualified proof-of-delivery, production custody/settlement, independent certification, or authorization for live/real-value trading.
