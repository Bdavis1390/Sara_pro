# Bitcoin Core 32.0 — governed external assurance benchmark

Upstream: `bitcoin/bitcoin`
Target release: `v32.0rc1` → `v32.0`
Worldshepherd status: **IMPLEMENTED AS TEST DESIGN / NOT YET EXECUTED**
Execution environment: isolated local container or VM, `regtest` only, no real funds, no public-node exposure

## Purpose

Use Bitcoin Core 32.0 as an external, high-quality reference target for testing the Worldshepherd assurance doctrine:

> AI proposes or discovers → human reviews → PRIME authorizes → SARA executes bounded tests → ECHO captures provenance → OVERWATCH compares observed evidence with upstream truth → claims remain gated by evidence.

This benchmark deliberately separates **upstream-confirmed facts** from **Worldshepherd-observed facts**. Nothing in this document claims that Worldshepherd has reproduced a Bitcoin Core defect, confirmed a fix, measured a speedup, or contributed upstream until execution evidence exists.

## Current upstream anchors

As of 2026-09-17:

- Bitcoin Core `v32.0rc1` is the current release candidate.
- The project release schedule targets `v32.0` tagging on 2026-10-10; this is an aim, not a guarantee.
- The official 32.0 RC testing guide is explicitly work in progress and encourages independent additional testing.
- Block validation can prefetch input prevouts from chainstate in parallel. `-prevoutfetchthreads` defaults to 8 and permits up to 16 workers. Upstream: PR #35295.
- Upstream executable code and `test/functional/rpc_psbt.py` show `createpsbt`, `walletcreatefundedpsbt`, `converttopsbt`, and `psbtbumpfee` defaulting to PSBT v2 and accepting `psbt_version` to request a specific version. The draft release-notes page currently says `walletcreatepsbt`; this benchmark follows the executable RPC name `walletcreatefundedpsbt`. Upstream: PR #21283 / BIP 370.
- `estimatesmartfee` combines block-policy and mempool-policy estimators. Upstream: PR #34075.
- Non-Windows `-walletnotify` placeholder handling was hardened because a suitably authorized RPC caller able to create wallets could craft a wallet name that resulted in arbitrary command execution when `-walletnotify` was configured. Upstream: PR #36048.
- The HTTP server was rewritten for v32, enforces an 8192-byte maximum header size, adds `-rpcmaxconnections` defaulting to 16, and immediately disconnects clients outside `rpcallowip`. Upstream: PRs #35182 and #35592.
- Private broadcast receives additional resource/attempt bounds, including a 10,000-entry queue and 1,000-attempt per-transaction limit. Upstream: PRs #35406 and #35680.

Primary references:

- https://github.com/bitcoin/bitcoin/issues/35122
- https://github.com/bitcoin-core/bitcoin-devwiki/wiki/32.0-Release-Candidate-Testing-Guide
- https://github.com/bitcoin-core/bitcoin-devwiki/wiki/32.0-Release-Notes-Draft
- https://github.com/bitcoin/bitcoin/blob/master/test/functional/rpc_psbt.py

## Benchmark architecture

### SARA — bounded orchestrator

SARA owns the test state machine and may execute only predeclared test actions inside the isolated environment. It MUST NOT:

- connect the test node to mainnet;
- use wallets containing real keys or funds;
- run arbitrary shell payloads supplied by an AI analysis node;
- publish a vulnerability result automatically;
- modify upstream Bitcoin Core repositories.

### PRIME — authorization boundary

PRIME must authorize every transition from analysis to active execution. Minimum gates:

1. `SOURCE_PINNED` — exact Bitcoin Core tag/commit recorded.
2. `TEST_PLAN_REVIEWED` — expected behavior and failure criteria human-readable.
3. `SANDBOX_CONFIRMED` — regtest, disposable datadir, network restrictions verified.
4. `EXECUTION_APPROVED` — active test allowed.
5. `CLAIM_REVIEWED` — evidence sufficient for the proposed claim class.
6. `EXTERNAL_DISCLOSURE_APPROVED` — required before any upstream issue/PR/comment.

### ECHO — provenance/evidence ledger

Every test run records at minimum:

```json
{
  "benchmark": "bitcoin-core-32",
  "case_id": "BC32-XXX",
  "upstream_ref": "v32.0rc1",
  "commit": "<git commit sha>",
  "build": {
    "compiler": "<compiler/version>",
    "cmake": "<version>",
    "host": "<kernel/os/arch>"
  },
  "isolation": {
    "network": "regtest-only",
    "datadir": "disposable",
    "real_funds": false
  },
  "authorization": {
    "prime_gate": "<approval id>",
    "operator": "<human/operator identity>",
    "timestamp": "<UTC>"
  },
  "inputs_sha256": "<digest>",
  "stdout_sha256": "<digest>",
  "stderr_sha256": "<digest>",
  "result": "PASS|FAIL|INCONCLUSIVE",
  "claim_class": "<Worldshepherd claims-control label>"
}
```

Logs should be append-only or content-addressed after collection.

### OVERWATCH — independent comparison

OVERWATCH should display:

- expected behavior from upstream documentation;
- observed behavior from the pinned build;
- baseline behavior from a previous release or pre-fix commit when safely available;
- environmental differences;
- whether the evidence supports, contradicts, or cannot resolve the hypothesis;
- whether the result is reproducible across repeated runs.

OVERWATCH must distinguish a process being alive from the target behavior being correct.

## Test cases

### BC32-001 — PSBT v2 compatibility boundary

**Question:** Do the changed RPC defaults produce PSBT v2, and can an integration explicitly request legacy behavior where supported?

**Method:**

- start `v32.0rc1` in regtest;
- create a disposable descriptor wallet;
- exercise `createpsbt`, `walletcreatefundedpsbt`, `converttopsbt`, and `psbtbumpfee`;
- decode the resulting PSBTs and record version;
- repeat while explicitly requesting PSBT v0;
- compare JSON/RPC error shapes with v31.1 where relevant.

**PASS:** each tested v32 default decodes as PSBT v2 and each explicit legacy request decodes as PSBT v0.

**Failure classes:** `DEFAULT_VERSION_MISMATCH`, `OVERRIDE_MISMATCH`, `RPC_SCHEMA_MISMATCH`.

**Claims boundary:** a pass demonstrates only the tested RPC behavior on the pinned build; it does not prove compatibility with third-party wallets.

**Executable probe:** `external_anchor_pilots/bitcoin_core_32_psbt_probe.py`.

### BC32-002 — fee-estimator selection semantics

**Question:** Does `estimatesmartfee` expose the documented combined-estimator behavior and explicit estimator selection?

**Method:**

- use a controlled regtest workload with scripted transaction/mempool conditions;
- query default, `block_policy`, and `mempool_policy` modes;
- capture estimator field, errors, and health statistics;
- repeat across sparse and populated mempool conditions.

**PASS:** selection and failure behavior match the documented v32 contract.

**Failure classes:** `ESTIMATOR_SELECTION_MISMATCH`, `HEALTH_GATE_MISMATCH`, `PERSISTENCE_MISMATCH`.

### BC32-003 — walletnotify command-injection regression

**Question:** Does the patched placeholder path treat wallet names literally rather than permitting shell interpretation?

**Safety rule:** do not use a destructive or general-purpose command payload. Use upstream regression coverage or a benign isolated canary whose only possible effect is a disposable marker inside the test container.

**Method:**

- pin the release-candidate commit;
- inspect/execute the upstream regression test associated with PR #36048;
- configure `walletnotify` only inside the disposable container;
- provide edge-case wallet names that exercise placeholder escaping;
- verify the notification receives the literal wallet identity and no out-of-band canary side effect occurs.

**PASS:** literal handling is preserved and the canary cannot escape the intended notification argument.

**Failure classes:** `PLACEHOLDER_INTERPRETATION`, `OUT_OF_BAND_EXECUTION`, `REGRESSION_TEST_FAILURE`.

**Disclosure gate:** any unexpected result remains private until independently reproduced and human-reviewed.

### BC32-004 — HTTP resource-boundary regression

**Question:** Does the rewritten HTTP service enforce documented header and connection limits without unbounded resource growth?

**Method:**

- launch the RC in a memory-capped container;
- confirm the 8192-byte header boundary behavior;
- confirm clients outside allowed RPC address policy are rejected/disconnected as documented;
- exercise simultaneous connections around the configured `rpcmaxconnections` limit;
- record RSS, open descriptors, connection count, response codes, disconnect behavior, and recovery after load stops.

**PASS:** limits are enforced and resource consumption returns to a stable envelope after bounded load.

**Failure classes:** `HEADER_LIMIT_BYPASS`, `CONNECTION_LIMIT_BYPASS`, `RESOURCE_GROWTH`, `RECOVERY_FAILURE`.

### BC32-005 — parallel prevout correctness

**Question:** Does prevout prefetch improve throughput without changing block-validation results?

**Method:**

- pin identical block data and cache conditions;
- run with `-prevoutfetchthreads=0`, `1`, `8`, and `16`;
- record wall time, CPU time, I/O counters, peak RSS, tip hash, UTXO commitment/available validation invariants, and logs;
- repeat enough times to report distributions rather than one best run.

**PASS:** validation outcome is invariant across thread settings; performance differences are reported with confidence intervals and environment metadata.

**Failure classes:** `VALIDATION_DIVERGENCE`, `NONDETERMINISTIC_STATE`, `PERFORMANCE_REGRESSION`, `INSUFFICIENT_SAMPLE`.

**Claims boundary:** do not claim “3x faster” unless the Worldshepherd test environment actually measures that result; upstream benchmark ranges remain attributed to upstream.

### BC32-006 — private-broadcast boundedness

**Question:** Are the documented queue and retry limits visible and enforced under controlled regtest-compatible testing?

**Method:** prefer direct unit/functional regression coverage from upstream over synthetic public-network behavior. No attempt should be made to infer anonymity or privacy guarantees from a local test.

**PASS:** configured/default bounds match upstream implementation and tests.

**Claims boundary:** local enforcement testing does not demonstrate real-world sender anonymity.

## Before/after strategy

Where feasible, compare:

1. previous stable (`v31.1`),
2. vulnerable/pre-fix commit only if safe and required,
3. `v32.0rc1`,
4. subsequent RCs,
5. final `v32.0` once tagged.

A vulnerability regression should be considered especially strong only when the same bounded harness demonstrates the expected failure on the relevant pre-fix code and the expected safe behavior on the patched code. If the pre-fix case cannot be safely executed, mark the result `INCONCLUSIVE` for reproduction and rely on code/test inspection instead.

## Acceptance ladder

### Gate A — design complete

- source references pinned;
- threat/failure contracts defined;
- safety boundaries defined;
- evidence schema defined.

Claim: **IMPLEMENTED IN SOFTWARE** only if the orchestration/evidence machinery exists; otherwise **PROVEN INTERNALLY** is not permitted.

### Gate B — harness executes

- deterministic environment launches;
- PRIME approvals are logged;
- ECHO captures artifacts;
- OVERWATCH renders expected vs observed;
- no public network dependency.

Claim: **PROVEN INTERNALLY** for orchestration behavior only.

### Gate C — technical reproduction

- target behavior reproduced repeatedly;
- controls included;
- environment and commit pinned;
- independent rerun succeeds.

Claim: **PROVEN INTERNALLY** for the specific reproduced property.

### Gate D — upstream corroboration

- result compared with upstream tests/fix/maintainer response;
- discrepancies resolved or explicitly recorded.

Claim: **SUPPORTED BY LITERATURE** or **PARTNER VALIDATION** only where the external evidence actually supports it.

### Gate E — contribution

- disclosure approved;
- minimal reproducer/test or documentation improvement prepared;
- no exaggerated security or performance claim;
- upstream submission recorded separately from acceptance/merge.

## Immediate execution sequence

1. Keep this benchmark on a review branch until the harness exists.
2. Add an isolated Bitcoin Core RC runner (container or disposable VM).
3. Execute BC32-001 first: low risk, deterministic, fast, and directly relevant to integration breakage.
4. Implement BC32-004 second: validates Worldshepherd resource-boundary monitoring against a real network service rewrite.
5. Implement BC32-003 using upstream regression coverage, not an improvised exploit payload.
6. Implement BC32-005 after the environment can reliably capture storage/cache/performance metadata.
7. Re-run the entire suite for every subsequent 32.0 RC and final v32.0.

## Current claim state

- Benchmark specification: **IMPLEMENTED IN SOFTWARE** as repository test design.
- BC32-001 executable probe: **IMPLEMENTED IN SOFTWARE / NOT YET EXECUTED**.
- Bitcoin Core defect reproduction by Worldshepherd: **NOT CURRENTLY CLAIMED**.
- Bitcoin Core fix validation by Worldshepherd: **NOT CURRENTLY CLAIMED**.
- Worldshepherd performance measurement of v32: **NOT CURRENTLY CLAIMED**.
- Upstream facts listed above: **SUPPORTED BY LITERATURE / PRIMARY UPSTREAM SOURCES**.

This separation is intentional. The benchmark becomes valuable when evidence advances the claims, not when labels advance ahead of evidence.
