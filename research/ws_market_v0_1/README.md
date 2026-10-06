# WS-MARKET v0.1

WS-MARKET v0.1 is a deliberately small proof-of-concept kernel for the DARPA **Influence Benchmarks for AI Systems** topic.

It is **not** a completed DARPA Phase I environment and does not claim validated bias detection or the program's target allocative efficiency across a representative benchmark corpus.

## Implemented in v0.1

- deterministic sealed-bid second-price market;
- dynamic news events that alter agent valuations;
- interchangeable deterministic agent behavior;
- hash-chained event ledger;
- duplicate-event rejection;
- exact replay digest for equivalent inputs;
- allocative-efficiency calculation;
- initial bid-shading classifier.

## Evidence posture

Claim state:

- `IMPLEMENTED IN SOFTWARE`
- `PROVEN INTERNALLY` for the bounded unit-tested behaviors
- `REQUIRES PARTNER VALIDATION` / program-specific validation for any DARPA-facing performance claim

## Run tests

From repository root:

```bash
python -m unittest research.ws_market_v0_1.test_ws_market -v
```

## Next gates

1. Add continuous double auction.
2. Add black-box HTTP/process agent adapter.
3. Add experiment manifest binding prompts, model identifiers, seeds, versions, and market configuration.
4. Add dynamic news generators with controlled perturbations.
5. Add classifier plug-in API and uncertainty reporting.
6. Add multi-run statistical comparison.
7. Add stock-agent harness capable of exercising multiple LLM providers without hard-coding provider credentials.
8. Add resource/performance profiling.
9. Bind run artifacts into ECHO/evaluator-handoff format.
10. Benchmark against accepted human/economic reference data.

## Claims boundary

The current code demonstrates software mechanics only. It does not establish:

- human-equivalent market behavior;
- >90% allocative efficiency across a representative suite;
- valid psychological or cognitive-bias diagnosis;
- deception detection validity;
- generalization across LLM families;
- DARPA acceptance or sponsorship.
