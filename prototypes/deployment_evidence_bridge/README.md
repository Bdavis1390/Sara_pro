# Worldshepherd deployment-evidence bridge — reference PoC v0.2

**Status: SIMULATED ONLY / PROTOTYPE.** No authenticated Kubernetes/GitOps runtime observation, no production use, no independent attestation, no certification, and no NIS2 or ISO/ISMS conformity determination.

This standard-library Python example joins **operator-supplied** deployment records with **operator-supplied** CycloneDX JSON and vulnerability finding references. It exports an evidence-oriented JSON report and CSV application-component inventory. It does not ingest credentials or contact external APIs.

## Run

From any directory:

```bash
cd /path/to/ws_deployment_evidence_bridge_v0_2
python3 bridge.py --input examples/deployments.json --out /tmp/ws-evidence-out
python3 -m unittest discover -s tests -v
```

File layout: `bridge.py`, `tests/test_bridge.py`, `examples/{deployments,sbom,findings}.json`.

## Deliberate evidence model

- **Deployment instance:** application + environment + cluster + namespace, keyed with an unambiguous canonical JSON tuple digest, rather than concatenated identifiers.
- **Declared desired state:** GitOps revision, canonical HTTPS project URL, desired OCI-style SHA-256 digest; values supplied by the operator, not validated against Git or an image registry.
- **Reported observation:** source, timezone-aware timestamp, digest. Alignment is `MATCH_REPORTED`, `DRIFT_REPORTED`, or `UNVERIFIED`; `independently_verified=false` always.
- **Reported freshness:** `RECENT_REPORTED`, `STALE_REPORTED` after 24 hours, or `NOT_OBSERVED`. Future timestamps more than five minutes ahead of the report time are rejected. Freshness is not source authenticity.
- **Composition:** CycloneDX component name/version/purl, plus hash of input SBOM bytes. The format has *minimal checks only*, **not** formal CycloneDX schema validation or dependency completeness.
- **Findings:** count and source SHA-256 only; raw vulnerability findings are not copied into outputs. No vulnerability scan, exploitability assessment, VEX decision, or vulnerability remediation is claimed.
- **Controls:** regulatory status is always `NO_COMPLIANCE_DETERMINATION` with explicit evidence gaps. An ISMS assessor must interpret any exported evidence separately.

## Input and export security

All referenced files resolve within the input manifest directory (including symlink protection); files are limited to 10 MB, at most 1,000 deployment rows and 10,000 components/findings. Required identifiers reject ASCII control characters, HTTPS URLs reject embedded credentials/query/fragment, and output CSV prevents common spreadsheet formula injection by prefixing an apostrophe to formula-like cells. JSON is emitted without arbitrary finding bodies. Output files are atomically replaced **individually**; the pair is not a transaction and there is no attestation of producer identity. Hashes alone provide integrity references, not independently trusted authenticity.

**Additional work before handling untrusted production data:** authenticated ingestion and authorization, comprehensive CycloneDX JSON schema validation, OCI digest binding to a trusted runtime observer, signed statements with trust-root verification, validation of findings/VEX formats, coordinated multi-file transactions, tenant-level isolation and redaction policy, and independent security assessment. No secrets, regulated personal data, protected information or CUI should be inserted into this PoC.

## Interoperability / OpenSSF discussion

The prototype is **not a GUAC replacement**: it deliberately sits between desired/observed deployment inventory, artifact identity, and software supply-chain graph/ISMS consumers. Ask GUAC and OpenSSF maintainers whether deployment identity and observation evidence can be represented by existing in-toto/OCI/GUAC primitives before proposing a new upstream schema. Do not imply recognized Technical Initiative status or eligibility for TI funding.

Prior Worldshepherd use-case discussion: https://github.com/Bdavis1390/Sara_pro/issues/426