# OCSF Agent Trust-Base Conformance Pilot

**Status:** provisional / non-normative reference artifact

**Upstream target:** `ocsf/ocsf-schema#1724` — *Discovery: agent trust-base inventory, applying record_integrity per emission*

This pilot turns the semantic requirements being discussed in OCSF issue #1724 into executable structural test vectors. It is deliberately **not** an alternate OCSF schema and does not claim that the proposed class has been accepted.

The pilot is grounded in concepts already present on OCSF `main`, including:

- `metadata.uid`
- `ai_agent.uid` and `ai_agent.instance_uid`
- the `record_integrity` profile
- `attestation.chain_uid`
- `attestation.prev_event`
- `fingerprint` objects

## What it checks

The current verifier enforces these provisional invariants:

1. Every emission has `metadata.uid`.
2. Every emission identifies `ai_agent.instance_uid`.
3. `attestation.chain_uid` is scoped to the same agent instance.
4. Genesis emissions omit `prev_event`; no `GENESIS` sentinel is accepted as a fingerprint value.
5. Non-genesis emissions link to the immediately preceding event UID and fingerprint.
6. One record shape is emitted at two firing points: `admission` and `closure`.
7. An unmatched admission is a structural failure.
8. Declared and observed trust-base states are both retained; divergence is evidence and is **not** itself a validator failure.
9. Local artifacts such as adapters, tool schemas, policy bundles, and charters carry content fingerprints.
10. Remotely hosted models use an identity tuple (`ai_provider`, `name`, `version`) rather than pretending the producer can hash unavailable weights.
11. Credential references and scopes may be represented, but raw credential material keys are rejected.

## Test vectors

`fixtures.json` currently includes six scenarios:

- session-start baseline — expected pass
- MCP/tool-schema refresh with benign declared/observed divergence — expected pass
- adapter digest divergence — expected pass as evidence, not a schema verdict
- missing closure emission — expected fail
- broken `prev_event` chain — expected fail
- raw credential material present — expected fail

## Run

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_trustbase.py \
  external_anchor_pilots/ocsf_agent_trustbase/fixtures.json
```

The command exits non-zero only when an actual result disagrees with a fixture's declared expectation.

## Important boundary

This verifier does **not** implement OCSF canonical serialization, cryptographic signature verification, or final field names for the proposed trust-base inventory class. Those should remain aligned to upstream OCSF decisions and existing validator/compiler behavior.

The intended upstream contribution is the **conformance-test slice**: once the class PR stabilizes, translate these invariants and vectors into the exact accepted OCSF fields and, where maintainers agree, integrate suitable checks into the existing validator/CI path.
