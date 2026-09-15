# WS-SARA-EVAL-v1 — Installation Checklist

Use only with the frozen source baseline `1c7be6c51ffd475f124e951f6c8c76208460b895`.

This checklist is an evaluator aid, not evidence of external reproduction until an external evaluator completes it in an evaluator-controlled environment.

## Preflight

- [ ] record exact source SHA
- [ ] record OS / architecture
- [ ] record Python version
- [ ] record Docker / Compose versions if used
- [ ] record dependency installation method
- [ ] confirm no production/customer/CUI/classified data are present
- [ ] confirm localhost-only publication unless the evaluator deliberately changes the network boundary and records that deviation

## Python local path

The frozen README documents the following local setup sequence:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
# Replace both tokens with different random values.
./scripts/start_interface.sh
```

Evaluator must use its own credentials/tokens and retain no Worldshepherd production secrets.

## Documented local surfaces

Default local UI: `http://127.0.0.1:9530/ui`

Documented surfaces at the frozen baseline include:

- `/health`
- `/livez`
- `/readyz`
- `/v1/relay`
- `/v1/audit?limit=50`
- `/admin/registry`
- `/admin/selftest`

## Acceptance record

For each step record:

- command or action;
- exit/result status;
- relevant output hash or artifact reference;
- discrepancy ID if behavior differs from the reviewed instructions.

## Claims boundary

A successful installation proves only that the reviewed frozen software can be installed in the recorded environment. It does not by itself establish independent functional reproduction, production readiness, customer acceptance, regulatory conformity, or physical capability.
