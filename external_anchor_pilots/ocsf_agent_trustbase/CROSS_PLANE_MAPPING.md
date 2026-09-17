# Cross-Plane Mapping — OCSF Agent Activity vs Trust-Base Evidence

**Status:** provisional design aid for `ocsf/ocsf-schema#1724`; not an OCSF specification.

## Purpose

This document keeps the Worldshepherd trust-base pilot aligned with the direction of current OCSF AI work without duplicating OCSF event semantics.

The design separates two complementary planes:

- **Behavior / activity plane** — what the agent or runtime did.
- **Configuration / evidence plane** — what the agent was configured to be, what dependencies actually resolved, and whether the resulting evidence chain is complete and tamper-evident.

The two planes should correlate; they should not be collapsed into one event taxonomy.

## Behavior / activity plane

When an agent action is already representable by an existing OCSF event class, use that class and attach the relevant AI context instead of emitting a second semantically duplicative AI event.

Examples:

| Agent action | Preferred OCSF representation | Trust-base pilot role |
|---|---|---|
| reads or deletes a file | File System Activity | correlate to the trust-base state active when the action occurred |
| launches a shell or child process | Process Activity | correlate to the trust-base state and policy/configuration in force |
| invokes an HTTP/API endpoint | API Activity | correlate to active tool/schema/model/policy state |
| performs an agent-specific lifecycle action not represented elsewhere | AI Agent Activity candidate (`#1754`) | correlate, but do not redefine the activity |
| reports completion/permission/compaction/sub-agent outcome state | `ai_status` candidate from `#1704` | use as outcome context; do not duplicate outcome taxonomy in trust-base inventory |

This follows the direction under discussion in `#1754`: existing OCSF actions should remain in their native activity classes where possible, while AI-specific activities cover genuinely agent-specific events.

## Configuration / evidence plane

The trust-base inventory proposal in `#1724` addresses a different question: what discrete configuration constituted the agent trust base at a given point, and did the resolved state match the declared state?

The pilot therefore remains focused on:

- stable and instance-level agent identity;
- declared configuration vs resolved/observed configuration;
- model identity/version or content digest when the bytes are locally available;
- adapter, tool-schema, policy-bundle, and charter fingerprints;
- credential references and scopes without credential material;
- admission-time evidence before newly introduced dependencies execute;
- closure-time evidence after the operation boundary closes;
- `record_integrity` chain continuity across emissions;
- structurally detectable missing emissions or broken predecessor linkage.

## Correlation rule

The two planes should share enough identity and correlation context for a consumer to answer:

> Which trust-base state was active when this activity occurred?

The exact OCSF correlation field should remain an upstream decision. Until the #1724 class stabilizes, the pilot must not hard-code a new normative correlation attribute.

At minimum, a future accepted mapping should allow correlation by some combination of:

- `ai_agent.uid`;
- `ai_agent.instance_uid`;
- event or operation correlation identifiers already accepted by OCSF;
- time/order information;
- the `record_integrity` chain identity for trust-base emissions.

## Non-duplication rules

The trust-base class should **not** become a second home for:

- file/process/API activity semantics;
- tool input/output payloads already represented by activity events;
- permission outcomes if `ai_status` or `security_control` carries the accepted form;
- stop-reason taxonomy already centralized in `ai_status`;
- compaction or sub-agent outcome taxonomies once centralized upstream;
- behavioral verdicts such as malicious/benign;
- producer-computed divergence verdicts when raw declared/resolved evidence can be emitted instead.

## Admission vs occurrence

PR #1754 introduces a candidate `is_pre_occurrence` concept for tool-use activity. That is useful evidence that OCSF is distinguishing pre-action from post-action telemetry, but the trust-base pilot should not assume that field will become the #1724 admission/closure mechanism.

The trust-base requirement remains semantic:

1. emit before a newly introduced dependency is permitted to execute;
2. emit again at the relevant closure boundary with the resolved/observed state;
3. preserve ordering and continuity through `record_integrity`;
4. let consumers compare records rather than embedding a producer verdict.

If OCSF later standardizes a shared pre/post occurrence pattern suitable for inventory events, the pilot can translate to it.

## Adoption test

Before any upstream translation, verify that a proposed #1724 implementation passes all of these separation checks:

1. an agent file/process/API action is not duplicated merely because an AI agent caused it;
2. `ai_status` outcome fields are referenced/reused rather than redefined;
3. trust-base records retain declared and resolved state as evidence;
4. trust-base records can be correlated to behavior/activity events;
5. `record_integrity` remains the only chain-of-custody mechanism;
6. no new field is presented as normative until accepted by OCSF maintainers.

This separation is the core interoperability goal: behavior tells a consumer **what happened**; trust-base inventory tells the consumer **what configuration was in force when it happened**.
