# Independent reproduction instructions — QCRYPTO + TSV v3.3

Purpose: reproduce the candidate's local software behavior and lineage checks without securities trading, real funds, transaction broadcast, production keys, or live regulatory communications.

1. Verify the release ZIP SHA-256 supplied with the package.
2. Verify `PARENT_BINDING_V3_3.json` against separately obtained parent artifacts when available.
3. Record OS, Python, OpenSSL, dependency versions, and reviewer identity/environment.
4. Run `python -m unittest discover -s tests -v`. Frozen expectation: **213 passed / 0 failed**.
5. Run `python scripts/generate_tsv_v3_3_evidence.py`.
6. Confirm `SOURCE_INTEGRITY_REPORT_V3_3.json` reports `satisfied: true`.
7. Confirm the local evidence summary binds both exact parent hashes.
8. Exercise fail-closed controls at minimum for: pre-exemption operation start; exemption expiry; late/missing Notice; business-day holiday input; affiliate denominator disagreement; Tier 1/Tier 2 threshold exceedance; duplicate affiliate ID; over-ten-minute transaction publication; incomplete transaction direction; missing 30-day public history; missing significant-event participant/SEC notice; malformed parent hash.
9. Inspect implementation paths, not only test output.
10. Do not connect a securities account, custody key, exchange account, production wallet, live trading venue, or Commission communication channel merely to reproduce this package.
11. If authoritative SIP/LULD/exchange feeds are later connected, document data licensing, provenance, clock synchronization, stale-data behavior, failover, and source identity separately.
12. Report skips, blocks, disagreements, and unsupported environments exactly as observed.

Reproduction does not establish SEC approval, legal compliance, registered exchange/ATS status, a production TSV, independent certification, Federal compliance, system-level FIPS validation, Bitcoin consensus PQ security, or authorization to trade securities.
