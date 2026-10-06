# WS-MARKET v0.2 — Black-Box Agent Probe

This increment adds a provider-neutral orchestration envelope for black-box AI agents.

## Added

- explicit agent identity descriptors;
- experiment manifest binding experiment ID, seed, market mechanism, code revision, prompt-template hash, scenario hash, and agent identities;
- deterministic manifest digest independent of declaration order;
- provider-neutral black-box agent protocol;
- JSON action validation;
- exact observation/action evidence in the existing hash-chained ledger;
- fail-closed descriptor, duplicate-observation, and output-shape checks.

## Why this matters

An AI-agent benchmark can produce misleading comparisons when the model version, prompt template, scenario, software revision, or observation sequence changes unnoticed.

WS-MARKET v0.2 therefore records the experiment envelope before interpreting behavior. It separates:

1. **what the agent was shown**;
2. **which black box produced the output**;
3. **what the black box returned**; and
4. **how downstream classifiers interpret that output**.

The adapter abstraction is intentionally vendor-neutral. Later integrations may call local models, hosted APIs, or government-provided agents without changing the evidence model.

## Evidence boundary

Current claim posture:

- **IMPLEMENTED IN SOFTWARE** for the v0.2 adapter/manifest machinery;
- **PROVEN INTERNALLY** only after the committed tests/CI pass;
- no claim that any commercial LLM provider has been integrated;
- no claim that model behavior is deterministic;
- no validated cognitive-bias/deception classifier claim;
- no DARPA sponsorship, acceptance, or milestone completion claim.

The orchestration ledger can be deterministic for the same returned black-box actions even when the underlying model is stochastic.

## Test

```bash
python -m unittest tests.test_ws_market_v0_2 -v
```

## Next gates

1. connect at least three lawful black-box model adapters;
2. bind exact prompt-template content through an artifact reference rather than hash alone;
3. add controlled dynamic news generation;
4. implement classifier plug-in uncertainty;
5. add repeated-run statistical comparisons;
6. add a continuous double auction;
7. scale toward the opportunity-specific multi-model benchmark.
