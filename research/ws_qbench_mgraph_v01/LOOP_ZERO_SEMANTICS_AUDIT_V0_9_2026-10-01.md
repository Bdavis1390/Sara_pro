# WS-QBENCH-MGRAPH v0.9 — loop zero-semantics audit

## Status

`SIMULATED ONLY / NEGATIVE REPRODUCTION EVIDENCE`.

The corresponding author clarified the intended rule: no tolerance, no hopping-order cutoff, sampling without replacement, and a loop is connected iff its full `2q` product is exactly nonzero in double precision. Supplementary Note S1 defines the probabilities over `2 x 10^4` realizations and requires

`pConnect = pNontrivial + pTrivial`.

This audit asks a stricter question: **is that verbal convention, combined with Worldshepherd's numerically stable closed-form Laguerre implementation, sufficient to reproduce the published S1 loop-formation behavior?**

The answer is currently **no**.

## Candidate results

Using `Nmax=200`, `20,000` realizations, without-replacement sampling, no threshold, and the repository stable displacement calculation:

| eta | q | pConnect | pNontrivial | pTrivial | nontrivial / connected |
|---:|---:|---:|---:|---:|---:|
|0.3|2|0.84885|0.34300|0.50585|0.4041|
|0.3|10|0.00030|0.00015|0.00015|0.5000|
|0.5|2|0.95565|0.38745|0.56820|0.4054|
|0.5|10|0.00630|0.00325|0.00305|0.5159|
|1.0|2|0.99660|0.42635|0.57025|0.4278|
|1.0|10|0.26395|0.13185|0.13210|0.4995|
|1.5|2|0.99985|0.45915|0.54070|0.4592|
|1.5|10|0.80620|0.39985|0.40635|0.4960|
|2.0|2|0.99980|0.47060|0.52920|0.4707|
|2.0|10|0.98920|0.49015|0.49905|0.4955|
|3.0|2|0.99975|0.49075|0.50900|0.4909|
|3.0|10|0.99920|0.49950|0.49970|0.4999|

No connected sample in these selected runs fell outside the author's 0/pi phase classes, so the probability identity is satisfied to floating precision.

## What matches

Two source-level features do appear:

1. higher-q loops turn on later with increasing eta;
2. once higher-q loops are well formed, approximately half are nontrivial.

These are qualitatively aligned with the manuscript.

## What fails

The stable-formula implementation drives `pConnect` for both `q=2` and `q=10` extremely close to one by `eta=2..3`.

The published Supplementary Figure S1 instead visibly retains q-dependent **sub-unity** high-coupling plateaus; the paper's main text describes the approach to the DSC regime only as exceeding 80% for q=2 and 40% for q=10, not converging both curves to unity.

This discrepancy is far larger than the binomial Monte Carlo uncertainty of the 20,000-realization candidate runs. For example, at `eta=2` the candidate q=10 result is `0.9892 +/- 0.00073` (one standard error).

## Revised source-lock interpretation

The author's clarification resolves the **logical rule** for G1, but not yet its implementation-specific floating-zero pattern.

Therefore G1 should be read as:

`RULE LOCKED / OPERATIONAL ZERO SEMANTICS REQUIRE CODE S1 VERIFICATION`

rather than as a completed exact-reproduction gate.

This does not contradict the author's answer. "Exactly nonzero in double precision" makes the concrete floating-point implementation scientifically relevant: different algebraically equivalent evaluations can produce different underflow/zero patterns in finite precision.

## Next gate

Do not tune a threshold to fit S1. That would violate the author clarification.

Instead:

1. acquire Code S1;
2. inspect the exact MATLAB Laguerre/factorial evaluation path;
3. hash the three source files;
4. rerun the same sampled eta/q points using Code S1;
5. compare zero masks of the hopping matrix before comparing Monte Carlo curves.

Until then, exact Supplementary Figure S1 reproduction remains `NOT CURRENTLY CLAIMED`.
