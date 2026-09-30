# QCRYPTO + TSV v3.6 recovery provenance — 2026-09-30

Original custody artifact: `worldshepherd_qcrypto_tsv_compliance_v3_6.zip`

Original SHA-256: `b5dd926055960847f4fd6fc1540214ed306bfbd93310825c7117b7355b90bfbc`

The Git replay retains all non-log source, tests, scripts, documentation, manifests, external fixtures, plus the five evidence fixtures required by the full regression suite. Historical logs and non-required evidence remain in off-host custody rather than being duplicated into Git.

Fresh pre-import replay: **301 PASS / 0 FAIL**. GitHub recovery validation also completed **301 PASS / 0 FAIL** using `python:3.12-trixie` with OpenSSL 3.5.7, preserving the live ML-DSA/SLH-DSA FIPS 204/205 scope-parity test.

Python dependencies used for recovery validation: pytest 9.0.2, cryptography 46.0.4, boto3 1.43.18, botocore 1.43.18.

Claims remain bounded to implemented/tested software behavior. This recovery does not establish production deployment, live-value authorization, post-quantum security certification, regulatory compliance, independent validation, or movement of value.
