# WS-CAE Adoption Blockers

Status date: 2026-09-13

This document records whether a rational external project still has reasons to decline WS-CAE adoption. It is intentionally stricter than promotional material.

| Potential blocker | State | Current mitigation |
|---|---|---|
| Requires consensus/protocol change | CLOSED | Profile-only adoption changes no chain protocol |
| Requires a signature-scheme change | CLOSED | WS-CAE describes authority state; it does not prescribe algorithms |
| Requires Worldshepherd runtime | CLOSED | JSON profile semantics are independently implementable |
| Requires chain-specific SDK | CLOSED | Reference CLI is Python stdlib-only and optional |
| Cannot represent pre-PQ chains honestly | CLOSED | `ROADMAP`, `DRAFT`, `DEVNET`, `TESTNET`, `MAINNET`, `NONE`, and `PLUGGABLE_AUTH_ONLY` permit truthful incomplete states |
| Forces all consumers to share one risk appetite | CLOSED | Consumer policies are independent from chain profiles |
| Hides account-vs-consensus distinction | CLOSED | Consensus state is modeled separately and regression-tested |
| Encourages roadmap claims to look deployed | CLOSED | Maturity is explicit and fail-closed |
| Vendor lock-in | SUBSTANTIALLY MITIGATED | Equivalent evidence is accepted; schemas and semantics can be reimplemented independently |
| Moving-interface risk | SUBSTANTIALLY MITIGATED | `0.1.0-research` marker, compatibility rules, immutable-commit pinning guidance |
| Opaque governance / semantic capture | SUBSTANTIALLY MITIGATED | Public change-control, anti-capture, disagreement-preservation, and version-transition rules |
| No executable deployment path | CLOSED | CLI, schemas, composite action, consumer policy, reference profiles, and CI self-test are deployed on PR #218 |
| No evidence that consumer policy works independently | CLOSED INTERNALLY | Reference and consumer-policy paths execute independently in CI; external reproduction remains pending |
| No independent reproduction | OPEN | Issues #214 and #217 invite independent reproduction and prior-art challenge |
| No external chain adoption | OPEN | Adoption RFC and issue #219 provide the public adoption challenge; no external chain endorsement is claimed |
| No standards-body adoption | OPEN | WS-CAE is positioned as a profile/contribution candidate, not a standard |
| Explicit open-source/content license for external reuse | OPEN — REQUIRES LEGAL/IP DECISION | Repository currently has no detected license; the research steward should choose and publish terms appropriate to code, schemas, and documentation after legal review |
| Independent security review of reference implementation | OPEN | Reference tool is read-only and small, but external review is still desirable |

## Determination

Technical non-adoption is increasingly difficult to justify on integration-cost grounds because profile-only adoption is non-invasive and useful before PQ deployment.

However, universal "non-adoption makes no sense" is not yet a defensible claim while explicit reuse licensing, independent reproduction, and external adoption remain open.

The highest-priority blocker that cannot be closed purely by engineering is licensing. Choosing license terms changes legal rights and should not be done silently by the reference implementation.

## Promotion gate

A materially stronger adoption claim becomes defensible when:

1. explicit reuse terms are published;
2. at least one independent party reproduces two profiles or publishes a reasoned disagreement;
3. at least one external relying party consumes a profile or policy independently;
4. at least one external chain or wallet project publishes a profile, equivalent mapping, or concrete rejection rationale.
