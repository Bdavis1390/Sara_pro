# OPA #8772 — load-aware health and backpressure review

Date: 2026-09-12

Claims state: **SOURCE-CONFIRMED SEMANTIC-HEALTH GAP / DESIGN REQUIRES MAINTAINER AGREEMENT / NOT UPSTREAM ACCEPTED**

Upstream issue: `open-policy-agent/opa#8772`

## Executive finding

OPA #8772 is a high-fit Worldshepherd contribution candidate because it describes the same class of failure that the Worldshepherd semantic-health reference is designed to detect: the process is live and its plugin state is nominal, but the service is no longer meeting an operational contract.

OPA's current health behavior can confirm evaluation, bundle activation, and plugin state without expressing saturation. Current decision-log plugin source marks the plugin `StateOK` after starting its loop, while separate built-in counters already record decision-log drops from rate limiting and buffer-size limits. A deployment can therefore remain nominal from a plugin-health perspective while losing audit evidence.

No matching open fix PR was found during this review.

## Current-source evidence

Current OPA source reviewed for this record shows:

- `/health` is served by `unversionedGetHealth` and can incorporate bundle/plugin readiness;
- server health-policy input contains plugin-state/readiness information;
- the decision-log plugin marks itself `plugins.StateOK` when its processing loop starts;
- the decision-log plugin separately defines counters for events dropped because of rate-limit, buffer event count, and buffer byte-size limits;
- status-plugin code likewise has a bounded status buffer and a drop counter.

This establishes an important distinction:

> plugin liveness/readiness and evidence-delivery capacity are not the same state.

## Contribution scope should be narrower than "system load"

The issue proposes several potential saturation inputs, including in-flight request count, decision/status-log buffer pressure, and memory relative to `GOMEMLIMIT`.

Worldshepherd recommends **not** implementing all of those in a first patch.

Memory pressure and generic request saturation introduce broad runtime and deployment-policy questions. The decision/status log queues are a cleaner first target because OPA already owns their limits and drop semantics and because evidence loss is directly observable.

A staged design reduces compatibility risk.

## Phase 1 — evidence-pressure signal

Add an opt-in health/readiness mode that reports when decision/status evidence pipelines cross configured pressure thresholds.

Possible contract:

- existing `/health` remains unchanged by default;
- an explicit query/config option enables capacity checks;
- health can distinguish at least:
  - `healthy`: evidence queue under warning threshold;
  - `degraded`: queue pressure elevated but still accepting evidence;
  - `unready`: pressure exceeds readiness threshold or evidence is actively being dropped;
- response includes low-cardinality reason codes rather than raw high-cardinality plugin payloads.

If maintainers prefer standard HTTP only, `503` can represent unready while metrics/logs carry degraded state. If they accept richer body semantics, the response can expose the pressure reason without changing default readiness behavior.

## Phase 2 — request backpressure

Only after the health signal is defined should OPA consider config-gated request rejection with `503` and `Retry-After`.

Important ordering property:

> the client-backoff threshold should be reached before the pod is removed from rotation, so the server has a controlled degradation region rather than a cliff.

For example:

- warning threshold: 70%;
- request-backoff threshold: 85%;
- readiness threshold: 95%.

Exact values must be configuration, not hardcoded policy.

## Metric/source-of-truth requirement

Do not derive health by re-parsing logs.

The health decision should read the same internal counters/queue state that governs admission/drop behavior. Otherwise monitoring can diverge from the component that actually discards evidence.

For decision logs, the existing drop counters are strong evidence outputs but are cumulative, not instantaneous pressure. A readiness decision likely also needs current queue occupancy/capacity or an explicit recent-drop state.

If current queue internals do not expose occupancy safely, the first contribution can add read-only low-cost getters/metrics before wiring readiness.

## Failure semantics

Worldshepherd recommends separating:

- **LIVE** — OPA process and evaluation engine operate;
- **READY** — OPA can accept normal decision workload;
- **EVIDENCE_DEGRADED** — decision/status evidence path is pressured or dropping;
- **UNREADY** — configured saturation threshold indicates traffic should be routed elsewhere.

This avoids using one boolean to hide materially different operational states.

The naming exposed by OPA should follow maintainer conventions; these labels describe the semantic model, not a proposed public API.

## Regression matrix

Minimum tests should cover:

1. default behavior unchanged when load-aware checks are disabled;
2. queue below warning threshold => existing health succeeds;
3. queue above warning but below readiness threshold => process remains usable and degradation is observable;
4. queue above readiness threshold => opt-in health returns configured unready signal;
5. decision-log drop event => evidence-degradation signal/counter changes deterministically;
6. queue drains => readiness recovers without restart;
7. bundle/plugin health failure still dominates appropriately;
8. pressure metrics remain bounded-cardinality;
9. concurrent requests cannot race occupancy accounting negative/above capacity;
10. disabled decision logging does not incorrectly report evidence pressure.

If request backpressure is later implemented, add tests that `Retry-After` is only returned under the configured mode and threshold.

## Relationship to Worldshepherd semantic health

The existing Worldshepherd semantic-health reference uses the principle that `process_alive=true` is insufficient when the operational endpoint or telemetry contract is degraded/stale.

OPA #8772 is the policy-engine equivalent:

- process alive: true;
- policy evaluation: possible;
- plugin status: StateOK;
- evidence delivery: potentially dropping.

That makes this contribution a strong external validation case for the same architectural principle without requiring Worldshepherd-specific concepts in OPA.

## Contribution decision

**Classification: P0 / DESIGN + METRIC/REGRESSION CANDIDATE.**

Internal screening score: **95/100**.

The first upstream contribution should be a narrow design and regression proposal centered on evidence-pipeline pressure, not an all-purpose memory/load controller. Once maintainers agree on the health contract, implementation can reuse existing drop/limit semantics and add current-pressure observability where needed.
