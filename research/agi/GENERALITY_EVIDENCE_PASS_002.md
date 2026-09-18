# Generality Evidence Pass 002

Date: 2026-09-17
Status: IMPLEMENTED ON RESEARCH BRANCH / NOT PRODUCTION

## Highest-priority unmet gate

Broad independently human-referenced generality remains the highest-priority external qualification gap. Worldshepherd must not infer "most cognitive tasks" from one benchmark family or repeated runs of one evaluator.

## Fresh independent evidence checked

ARC Prize independently verifies GPT-6 Astra on ARC-AGI-3 at 62.7% under its Standard harness and 99.9% under its Provider Adapter harness. ARC Prize reports human-baseline action-efficiency superiority on 96% of completed levels, while explicitly warning that ARC-AGI-3 is bounded and does not establish AGI.

METR's current public time-horizon page was last updated 2026-05-08 and measures over 100 software-oriented tasks. METR explicitly notes measurements above 16 hours are unreliable with the current suite. Its public evidence therefore cannot supply broad cross-domain skilled-adult generality for Astra.

Conclusion: no Competent-AGI gap is closed by current independent evidence.

## Development improvement

`competence_evidence.py` now adds `GeneralityEvidencePolicy` and requires:

- human percentile at or above the configured threshold;
- non-provider independence;
- acceptable contamination risk;
- at least one independent-blind result by default;
- deduplication of repeated evidence from the same source/benchmark/harness;
- optional multiple independent sources per task family.

This prevents pseudoreplication: ten rows from one benchmark/harness can no longer masquerade as ten independent demonstrations of generality.

## Falsifier

This change is falsified as useful if it rejects genuinely independent replications merely because they share a benchmark name, or if duplicate rows can still inflate family coverage. The deduplication key is intentionally source + benchmark + harness and can be revised on evidence.

## Rollback

Revert commit `c244422d8cf9398762efcbe10755b1027465a43b` on `research/glyph-corpus-lsrp`.

## Claims ceiling

IMPLEMENTED IN SOFTWARE: evidence-policy hardening.

SUPPORTED BY EXTERNAL EVIDENCE: ARC-AGI-3 interactive performance and METR time-horizon scope/limitations.

NOT CURRENTLY CLAIMED: GPT-6 Astra is AGI; Worldshepherd is AGI; broad skilled-adult generality has been demonstrated.
