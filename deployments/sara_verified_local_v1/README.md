# SARA Verified Local v1

This deployment is the evidence-governed local administration, relay, PRE qualification, and bounded solver environment for Worldshepherd SARA.

## Astra solver profile

`Astra` is a Worldshepherd solver codename/profile. It is not a provider model identifier.

The current verified default OpenAI runtime target is `gpt-5.6-sol`, but network inference remains disabled by default. The implementation is in `worldshepherd_sara/astra_solver.py` and requires both an injected provider transport and explicit SARA model-inference authorization before a call can occur.

Fail-closed defaults:

- `SARA_ASTRA_MODEL=gpt-5.6-sol`
- `SARA_ASTRA_NETWORK_ENABLED=false`
- tool allowlist empty
- remote response storage disabled
- no embedded provider credentials
- no maturity upgrade from model output alone

See `../../docs/ASTRA_INTEGRATION.md` for the architecture and promotion gates.
