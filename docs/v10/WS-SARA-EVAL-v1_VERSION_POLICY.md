# WS-SARA-EVAL-v1 — Version Freeze Policy

`WS-SARA-EVAL-v1` remains pinned to source baseline:

`1c7be6c51ffd475f124e951f6c8c76208460b895`

Subsequent merges to `main`, including ECHO v1.6, do not retroactively change this evaluator target.

## Why

Independent reproducibility requires a stable target. Moving the source baseline after an evaluator has begun screening would contaminate the evidence chain and make results difficult to compare.

## Successor rule

A successor such as `WS-SARA-EVAL-v1.1` or `WS-SARA-EVAL-v2` may be created only by:

1. naming a new exact source SHA;
2. recording the delta from the prior baseline;
3. reviewing installation/dependency changes;
4. updating the protocol only where the new scope requires it;
5. preserving the original v1 evaluation record intact.

A pass on v1 must not be silently attributed to a successor release; changed behavior must be re-evaluated to the extent material to the claimed scope.
