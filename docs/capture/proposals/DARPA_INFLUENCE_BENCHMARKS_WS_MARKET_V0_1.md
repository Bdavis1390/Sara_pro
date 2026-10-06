# DARPA Influence Benchmarks Concept v0.1 — WS-MARKET

**Working title:** WS-MARKET — Provenance-Bound Dynamic Market Testbed for AI Influence and Bias
**Opportunity:** DARPA SBIR DPA26BZ06-DV026, Influence Benchmarks for AI Systems
**Official deadline verified:** 2026-10-21
**Status:** CONCEPT / Phase I candidate; entity and DSIP eligibility must be verified before submission

## 1. Topic fit

DARPA seeks a black-box test environment that uses economic frameworks to characterize latent behavioral preferences of AI systems in dynamic environments. The environment must support multiple agents, dynamic public information, economic decision structures, bias classifiers, and quantitative comparison of market outcomes.

WS-MARKET maps Worldshepherd's strongest existing software patterns onto that requirement:

- **SARA:** reproducible orchestration of agent experiments and scenario execution;
- **PRIME:** policy-constrained experiment control and explicit human authorization;
- **ECHO:** complete event, prompt, output, configuration, and decision provenance;
- **OVERWATCH:** live experiment telemetry, market metrics, and anomaly visibility;
- **PRE:** versioned requirement-to-test mapping and evaluator handoff.

## 2. Architecture

### Agent adapter
Treat each test AI as a black box. The adapter records only permitted inputs/outputs and experiment metadata; no internal model access is assumed.

### Market kernel
Pluggable market structures:
- sealed-bid auction;
- continuous double auction;
- posted-price market;
- multi-asset market.

### Dynamic news feed
A controlled stream of public-information events with:
- timestamp;
- source class;
- polarity / economic effect label;
- uncertainty;
- relevance to assets;
- experiment seed.

### Behavior classifier layer
Initial classifier families:
- bid shading / aggressiveness;
- loss aversion proxy;
- herding / conformity;
- overreaction / underreaction;
- strategic withholding;
- collusion-like coordination signals;
- deception indicators;
- susceptibility to another agent's stated beliefs.

These are measurable behavioral constructs, not moral labels.

### Evidence layer
Every experimental run binds:
- scenario;
- model/agent identity as provided by operator;
- model version where available;
- prompt template;
- input news sequence;
- bids/actions;
- outcomes;
- classifier outputs;
- software commit;
- random seed;
- market configuration;
- timestamps;
- exceptions.

## 3. Phase I milestone alignment

### Month 2
Deliver:
- market/testbed architecture;
- initial auction implementation;
- market-efficiency and utility metrics;
- dynamic news-feed schema;
- first behavior classifiers;
- reproducibility/evidence manifest.

### Month 6
Deliver:
- scale strategy;
- standardized agent decision-space schema;
- bid/event API;
- performance profiling;
- repeatable experiment batching.

### Month 9
Deliver:
- stock-agent suite representing at least 10 distinct LLMs, subject to lawful/API access and program rules;
- automated cross-agent comparison;
- model/version provenance;
- benchmark corpus.

### Month 12
Deliver:
- functional multi-agent test environment;
- replication of benchmark market patterns;
- measured allocative efficiency with the program target of >90%;
- comparative behavior analysis;
- exportable software/data/evidence package.

The >90% allocative-efficiency threshold is a program objective and is **not** claimed as currently achieved.

## 4. Core research hypotheses

H1: Behavioral differences among AI agents can be elicited more reliably when scenario changes are versioned and replayable.

H2: Event-level provenance reduces ambiguity between genuine adaptive behavior and experiment/configuration drift.

H3: Dynamic economic environments reveal interaction effects not visible in static prompt-response evaluations.

H4: Classifier uncertainty should be retained as first-class evidence instead of collapsing behavior into a binary safe/unsafe label.

## 5. Minimal proof of concept to build immediately

A local proof of concept should include:

1. two market mechanisms;
2. deterministic seeded market replay;
3. dynamic news events;
4. at least three interchangeable agent adapters;
5. event-sourced bid ledger;
6. market-efficiency metrics;
7. classifier plug-in interface;
8. ECHO-style evidence export;
9. failure injection for missing/stale/replayed events;
10. exact-run reproduction from a manifest.

## 6. Differentiation

The key differentiator is not simply "another agent benchmark." WS-MARKET makes the **experiment itself auditable**.

A result should be reconstructable as:

`requirement -> scenario -> model/agent -> prompt/input -> action -> market state -> outcome -> classifier -> metric -> evidence -> human review`

This allows investigators to distinguish model behavior from:
- scenario drift;
- prompt drift;
- software version changes;
- random-seed effects;
- model-version changes;
- missing events;
- data corruption.

## 7. Commercial transition

Potential non-defense customers:
- model developers;
- AI assurance vendors;
- financial/market simulation teams;
- regulated enterprises deploying AI agents;
- insurers / auditors evaluating AI operational risk;
- research institutions comparing adaptive agent behavior.

## 8. Claims boundary

Current Worldshepherd evidence supports software governance, provenance, reproducibility, replay, and evaluation-handoff patterns.

Not currently claimed:
- completion of the DARPA-specific economic testbed;
- >90% allocative efficiency;
- validated bias classifiers;
- 10-model stock-agent suite;
- DARPA sponsorship or acceptance.

Those are explicit development gates.
