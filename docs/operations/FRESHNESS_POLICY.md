# Worldshepherd Repository Freshness Policy

**Status:** `CANONICAL`

**Version:** 1.0

**Effective:** 2026-09-15

## Purpose

Worldshepherd accumulates executable software, dated evidence, active capture work, experiments, scientific hypotheses, partner-screening artifacts, and long-lived provenance. "Old" and "stale" are therefore not synonyms.

This policy prevents useful work from disappearing while also preventing historical material from masquerading as current truth.

## Freshness states

Every important artifact should be interpretable as one of these states:

| State | Meaning | Expected treatment |
|---|---|---|
| `CURRENT_CANONICAL` | current source of truth | linked from current navigation; updated on material change |
| `ACTIVE` | current work in progress | has a live owner/umbrella and next gate |
| `DATED_EVIDENCE` | immutable evidence for a bounded configuration/time | retain; supersede with new evidence rather than rewrite |
| `RECONCILE_REQUIRED` | useful unique work exists but base/context is no longer current | forward-port deliberately before merge/use |
| `SUPERSEDED` | a newer designated artifact replaces it | retain provenance and point to successor |
| `ARCHIVE` | historical/reference value, not current operating guidance | remove from default navigation but retain access |
| `SAFE_DELETE_AFTER_VERIFY` | no unique work remains and a successor/identical ref is proven | deletion may occur only after comparison/review |

## What counts as stale

An artifact is stale when using it as current guidance would materially misrepresent the present repository, evidence state, external facts, or operating plan.

Examples:

- a README says runtime packaging is fragmented after a canonical runtime has been merged;
- an opportunity brief says a solicitation is open after the deadline/status changed;
- an old PR describes itself as current even though a newer PR explicitly supersedes it;
- a workflow uses an unsupported/deprecated action/runtime when a supported migration exists;
- a branch is presented as authoritative although it is hundreds of commits behind and has a hardened successor;
- a capability table claims a lower or higher maturity than the current evidence supports.

## What is not automatically stale

The following may be old without being stale:

- test results bound to a historical commit;
- measurements with recorded configuration/calibration;
- negative experimental evidence;
- superseded architecture decisions retained for provenance;
- dated partner/opportunity screening retained as a historical snapshot;
- research hypotheses that are explicitly labeled and have not been falsified or promoted;
- archived source material needed to reproduce how a conclusion was reached.

Never rewrite dated evidence merely to make it look current.

## Review cadence by artifact class

| Artifact class | Freshness expectation |
|---|---|
| Root/profile README and canonical navigation | update immediately when source-of-truth paths or maturity change |
| Runtime/operator documentation | update in the same change as interface/command/endpoint changes |
| Canonical governance/claims/architecture docs | review on material change; explicit review at least every 30 days while actively evolving |
| Security/compliance readiness | review on control/tool/dependency change and at least every 30 days while active |
| Active opportunity/capture facts | re-verify against authoritative sources before external use; review at least weekly while active |
| Active partner/contact/outreach state | verify before action; do not infer response/validation from an old draft |
| Active PRs/branches | classify when materially behind `main`, superseded, or inactive for 14+ days |
| Dated evidence | immutable; no age expiry; supersede explicitly when new evidence changes interpretation |
| Research hypotheses/simulations | update when assumptions, evidence, or falsification state changes; age alone does not invalidate them |

The cadence is a review trigger, not permission to fabricate freshness. If authoritative re-verification is unavailable, mark the fact `UNVERIFIED` or `REQUIRES REVALIDATION`.

## Branch and pull-request lifecycle

### Keep active

Use `ACTIVE` when the branch/PR is based on a sufficiently current architecture, has a defined acceptance gate, and remains intended for incorporation.

### Reconcile required

Use `RECONCILE_REQUIRED` when:

- the branch contains unique useful work;
- `main` has materially changed its interface/security/claims architecture;
- direct merge would overwrite newer behavior or documentation; or
- the PR body/evidence refers to an obsolete base.

Forward-port the useful delta rather than merging the stale tree wholesale.

### Superseded

A branch/PR may be marked `SUPERSEDED` when a named successor contains or replaces its intended functionality/evidence. Prefer a comment linking the successor before closure.

### Safe deletion

A branch is `SAFE_DELETE_AFTER_VERIFY` only when at least one of these is demonstrated:

1. it has zero unique commits relative to a retained successor;
2. it points to the identical commit as a retained branch and the retained branch is the declared canonical name;
3. all unique changes are already present on `main` or a named successor and comparison confirms containment.

Names such as `duplicate`, `temp`, `old`, `please-ignore`, or `backup` are **not evidence** that deletion is safe.

## Evidence preservation

For evidence-bearing work:

- retain original date, configuration, commit/test identity and limitations;
- retain negative/anomalous evidence;
- identify superseding evidence rather than editing the old result;
- do not promote simulation to hardware evidence;
- do not promote internal tests to partner/government validation;
- do not let current prose erase a historically narrower failure or uncertainty statement.

## External dependency freshness

CI/action/dependency age is part of repository freshness.

- deprecated runtimes are migration triggers;
- action major-version upgrades require a reviewable PR and CI proof;
- security-sensitive actions should prefer maintained upstream releases and least-privilege permissions;
- dependency upgrades must not weaken existing checks merely to obtain a green build.

## Opportunity and external-fact freshness

PRE/capture material must keep **source freshness** separate from **Worldshepherd capability maturity**.

A new solicitation amendment can make an opportunity fact stale without changing Worldshepherd maturity. A new internal test can improve software evidence without changing the solicitation. These dimensions must never be collapsed.

## Current operating umbrellas

Freshness work routes through [`ACTIVE_TASKS.md`](ACTIVE_TASKS.md):

- #281 — Platform & Assurance
- #282 — Science & Validation
- #283 — Growth & Externalization

## Enforcement

The repository freshness workflow checks the stable source-of-truth contract and blocks known regression patterns. The dated freshness audit records broader branch/PR observations that are unsafe to auto-delete.

Machine checks supplement human review; they do not decide whether scientific evidence is valid or whether a historical branch has strategic value.
