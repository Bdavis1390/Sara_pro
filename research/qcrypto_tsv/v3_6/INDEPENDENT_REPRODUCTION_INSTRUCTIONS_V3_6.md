# Independent reproduction instructions — v3.6

Purpose: reproduce the v3.6 software behavior and evidence bindings without live trading, real funds, production private keys, or an assertion of regulatory compliance.

1. Verify the release ZIP SHA-256 supplied beside the package.
2. Record reviewer-controlled OS, Python, OpenSSL, dependency versions, and clock source.
3. Run `python -m unittest discover -s tests -v`. Frozen target: **301 PASS / 0 FAIL**.
4. Run `python scripts/generate_tsv_v3_6_evidence.py`; require exit code 0.
5. Confirm source integrity reports `satisfied=true` and source-manifest SHA-256 `c549be2fc7e7f29bd10eb4b1253fe911806a03f4ff8654ac947a6e9e3072dad2`.
6. Inspect `evidence/TSV_LOCAL_DURABLE_CURSOR_V3_6.json`: first sequence must ALLOW, next sequence after a fresh store instance must ALLOW, and the old sequence must DENY without advancing state.
7. Inspect `evidence/TSV_EXTERNAL_RESILIENCE_BUNDLE_V3_6.json`; verify its domain-separated SHA-256 is `ebc3b80d92ec8afca9be7c4265811358d41fbfeddd7f016ef5ef04a1fe2732a5` and all 10 cases match their recorded decisions.
8. Confirm the external terminal cursor is sequence 101 / revision 2 with state SHA-256 `1d6aa86f93ee64bbf9a43390b36d44ab2f28bb08bbaada8dcb8299749d4c92ca`.
9. Inspect `evidence/FLOOT_SECOND_PROVIDER_VALIDATION_V3_6.json`; the positive result must ALLOW with receipt `2a044c101f2e795b2637fe71089e0d75407aa909973fb1a50592545cc8417d6e`, and both mutation controls must DENY.
10. Confirm `evidence/FINAL_EVIDENCE_BINDING_V3_6.json` hashes to final evidence binding `c4ccd1edee4fe8ff85f708ff1db6f8acdd827cb3ad0c411ae6e05d3e5cbf9c02` under the stated domain.
11. Exercise additional negative cases locally: corrupt cursor state, stale provider health, contradictory provider partitions, stale calendar evidence, wrong calendar provider, and missing resilience context. They must fail closed.
12. Do not convert a test skip, unavailable external provider, stale evidence, or credential failure into a pass.

Reproduction establishes only the behavior and evidence actually observed. It does not establish licensed market-data access, authoritative market-calendar status, production availability, SEC approval, legal compliance, independent certification, or authorization to trade securities.
