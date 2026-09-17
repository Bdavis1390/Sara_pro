# OCSF Agent Trust-Base Conformance Pilot

**Status:** provisional / non-normative reference artifact; pilot CI validated

**Upstream target:** `ocsf/ocsf-schema#1724` — *Discovery: agent trust-base inventory, applying record_integrity per emission*

This pilot turns semantic requirements being discussed in OCSF issue #1724 into executable structural test vectors and analyzers. It is deliberately **not** an alternate OCSF schema and does not claim that the proposed class has been accepted.

The pilot is grounded in concepts already present on OCSF `main`, including:

- `metadata.uid`
- `metadata.correlation_uid`
- `ai_agent.uid` and `ai_agent.instance_uid`
- the `record_integrity` profile
- `attestation.chain_uid`
- `attestation.prev_event`
- `fingerprint` objects

It also tracks adjacent upstream AI work so the trust-base contribution does not duplicate behavior telemetry:

- `ocsf/ocsf-schema#1754` — draft `AI Agent Activity`
- `ocsf/ocsf-schema#1704` — shared AI outcome/status work under `ai_operation`

See `CROSS_PLANE_MAPPING.md` for behavior-vs-configuration separation, `ISSUE_1724_CONVERGENCE.md` for a discussion-state matrix, and `EVIDENCE_STRENGTH_AND_SAMPLING.md` for the current non-normative treatment of evidence strength and sampling/runtime drift.

## What it checks

The main trust-base verifier enforces these provisional invariants:

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

`verify_plane_separation.py` enforces the harness-level non-duplication boundary: behavior/outcome keys under discussion in adjacent OCSF work are rejected if copied into the provisional `trust_base` payload.

`verify_evidence_join.py` exercises the evidence-grade join discussed in #1724: the trust-base closure and correlated activity event must carry the same `metadata.correlation_uid`, and both records must carry an integrity attestation fingerprint. This is intentionally stronger than ordinary schema validity. It models the thread's principle that the join key should live inside the integrity-protected event rather than exist only as advisory external metadata.

`verify_evidence_strength.py` checks only internally testable consistency for the discussion-level `verification_id` vocabulary. It does **not** rank evidence or decide whether any evidence strength is sufficient for a security control.

`analyze_sampling_delta.py` reports structural differences between declared and observed sampling/runtime configuration. It preserves changed, declared-only, and observed-only states without filling defaults or assigning a security verdict.

OCSF's current `attestation` description states that canonical serialization covers the entire event except the attestation's own `fingerprint` and `signatures`; therefore, a present `metadata.correlation_uid` is within the attested event content.

## Test vectors

`fixtures.json` includes six trust-base scenarios:

- session-start baseline — expected pass
- MCP/tool-schema refresh with benign declared/observed divergence — expected pass
- adapter digest divergence — expected pass as evidence, not a schema verdict
- missing closure emission — expected fail
- broken `prev_event` chain — expected fail
- raw credential material present — expected fail

`plane_separation_fixtures.json` adds three architectural-separation scenarios:

- clean trust-base evidence with an external harness-only correlation reference — expected pass
- stop reason duplicated inside trust base — expected fail
- tool input duplicated inside trust base — expected fail

`evidence_join_fixtures.json` adds four correlation/integrity scenarios:

- matching integrity-protected closure/activity correlation — expected pass
- closure missing `correlation_uid` — expected fail
- mismatched closure/activity correlation — expected fail
- activity-side correlation not protected by an attestation fingerprint — expected fail

`evidence_strength_fixtures.json` adds six evidence-strength consistency scenarios:

- local adapter digest — expected pass
- provider-asserted hosted-model tuple — expected pass
- not-observable hosted-model tuple — expected pass
- locally computed claim without a digest — expected fail
- not-observable claim that also asserts a local fingerprint — expected fail
- unsupported verification ID — expected fail

`sampling_delta_fixtures.json` adds five reporting scenarios:

- stable sampling configuration
- gateway token-cap rewrite
- caller temperature override
- runtime-only constraint appearance
- runtime binding represented as structurally unavailable

## CI gate

`.github/workflows/ocsf-agent-trustbase-pilot.yml` provides a narrow GitHub Actions gate for this pilot. It compiles the Python tools, runs all expectation-based verifiers, executes the sampling/runtime analyzer, and validates its JSON output.

The dedicated **OCSF Agent Trust-Base Pilot** workflow completed successfully on the branch after the evidence-strength and sampling layers were added. That result validates the pilot's executable expectations; it does **not** imply OCSF maintainer review, acceptance, or upstream schema conformance.

## Architectural boundary

The pilot is a **configuration/evidence-plane** contribution.

It should not become a second event taxonomy for actions already represented by OCSF. File operations, process launches, API calls, and other existing activities should stay in their native OCSF classes with AI context attached where appropriate. Agent-specific lifecycle/action semantics belong with the emerging `AI Agent Activity` work, while shared outcome/status semantics should be reused rather than redefined if that architecture is accepted upstream.

The trust-base contribution instead answers the complementary question:

> What discrete agent configuration and dependency state was in force when an activity occurred, what strength of evidence supports each element, and is the evidence chain complete?

The exact final class mapping is still upstream design work, but the #1724 discussion now favors a join over an overlay, with closure correlated to the relevant activity event rather than importing activity semantics into the trust-base class.

## Run

Run the trust-base semantic fixtures:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_trustbase.py \
  external_anchor_pilots/ocsf_agent_trustbase/fixtures.json
```

Run the behavior/configuration plane-separation fixtures:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_plane_separation.py \
  external_anchor_pilots/ocsf_agent_trustbase/plane_separation_fixtures.json
```

Run the evidence-grade closure/activity join fixtures:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_evidence_join.py \
  external_anchor_pilots/ocsf_agent_trustbase/evidence_join_fixtures.json
```

Run the evidence-strength consistency fixtures:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/verify_evidence_strength.py \
  external_anchor_pilots/ocsf_agent_trustbase/evidence_strength_fixtures.json
```

Report declared-versus-observed sampling/runtime differences:

```bash
python external_anchor_pilots/ocsf_agent_trustbase/analyze_sampling_delta.py \
  external_anchor_pilots/ocsf_agent_trustbase/sampling_delta_fixtures.json
```

Use `--json` on the sampling analyzer for machine-readable output.

## Important boundary

These tools do **not** implement OCSF canonical serialization, cryptographic signature verification, final field names for the proposed trust-base inventory class, or policy sufficiency decisions. Those should remain aligned to upstream OCSF decisions and existing validator/compiler behavior.

The intended upstream contribution is the **conformance-test and evidence-analysis slice**: once the class PR stabilizes, translate suitable invariants and vectors into the exact accepted OCSF fields, preserve separation from existing activity/outcome semantics, and where maintainers agree integrate appropriate checks into the existing validator/CI path.
