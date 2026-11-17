# BAROS — Independent-Evaluator Synthetic Challenge Handoff v0.1

**Date:** 2026-11-17 | **RESEARCH ONLY — NOT A CLINICAL TEST OR APPROVED HUMAN-SUBJECTS PROTOCOL**

This file describes a reusable method for an independent investigator to author challenge cases without sharing reference labels with a developer until predictions are committed. It **does not establish** investigator independence, evidence provenance, real patient biological validity, data-access rights, commissioned TPS compatibility or dosimetric accuracy. Those require a qualified institution and separate agreements.

## Protocol ownership and preconditions

1. The independent evaluator defines and freezes the disease-site, biological measurement concept, use case, actual workflow (if any), and clinically meaningful failure taxonomy. Without institutional authorization, use **only synthetic inputs**. No PHI or real patient identifiers.
2. Evaluator locks a private case manifest with reference labels, rules for grading, ID linkage, and intended test coverage. Source case ID must be a deidentified synthetic token; no names, MRNs, dates of birth, patient images or device keys in code or GitHub. The evaluator records the entire case manifest SHA-256, independent versioning and custody separately before developer access.
3. The developer receives only inputs typed as `BlindCase` (prior state, current state, thresholds and source-evidence digest); expected strata (`qualified_trigger`, `disqualified_trigger`, `no_trigger`) are withheld. A readable source digest is **not evidence of a legitimate clinical source**.
4. Developer calls `run_blinded_challenge(cases, protocol_id=...)`. It uses the exact pre-TPS research decision contract and generates `BlindedSubmission` with run-level challenge/content SHA-256 and per-decision integrity audit digests. No clinical action is possible in this module.
5. The evaluator archives the software commit, dependency lock, challenge manifest hash, runner code, submission hash, full result object and environment metadata before releasing any reference label.
6. Only afterward, the evaluator supplies a complete held-out label map and calls `score_after_label_release(submission, held_out_labels)`. The tool verifies local submission integrity and required label coverage then computes descriptive Wilson intervals for false-proceed, qualified proposal recall and no-trigger spurious proposals. **Do not use these intervals as clinical safety claims**.
7. Every failure, invalid submission, rejected input, edge-case issue, abstention and unverifiable artifact must remain visible. Score and event-log authors must be distinct from whoever adjudicates clinical truth.
8. For future real-world use, institution-controlled signed provenance, legal data rights, IRB/ethics review as appropriate, independent instrument/TPS evaluation, blinded comparator adjudication and approved publication terms must be documented. A SHA-256 hash by itself is not an authenticated signature or proof of independent custody.

## Minimal example using synthetic cases

```python
from baros.blinded_challenge import BlindCase, run_blinded_challenge, score_after_label_release
# Build cases from explicitly SYNTHETIC BiologicalState and AdaptationThresholds.
# Hold reference_labels privately; do not include labels in BlindCase or its source.
submission = run_blinded_challenge(synthetic_cases, protocol_id="SYNTHETIC-PROTOCOL-V1")
# Archive submission before the independent evaluator reveals reference_labels.
# After independent release only:
score = score_after_label_release(submission, reference_labels)
```

The two variables in this example are supplied by an evaluator and are intentionally not invented by this README. For executable self-checks using only toy fixtures, see `tests/test_baros_blinded_challenge.py`.

## Input validation and known boundaries

- Existing BAROS controller now rejects ambiguous non-Boolean qualification flags, nonintegral phase indices, and non-Boolean forced-trigger flags.
- Longitudinal trigger comparisons require qualified prior **and** current states, rather than trusting the current measurement alone.
- A zero threshold means *any nonzero change* may trigger research evaluation; zero measured change alone must not cause a proposal. Manual force is an explicit, separately recorded research trigger that cannot bypass qualification.
- Exhaustive internal regression traverses 32 × 32 = 1,024 synthetic prior/current quality combinations, a **policy enumeration**, not independent evidence.
- The evaluator-owned challenge design must test adversarial cases not created or tuned by the software developer; current example cases in the repository are developer-authored.
- The code reports action eligibility, not an implemented biological-objective-to-TPS adapter; it generates **no** DICOM clinical plan, radiation prescription or dose.
- Real trial safety, physical-dose accuracy, clinical benefit, biomarker reproducibility, licensed dataset availability, and superiority over named vendor or scientific comparators are all **OPEN**.

## Release/communication gate

Do not send this as a claim of validated medical software. Use only as a proposed technical handoff to a qualified independent laboratory if it accepts the study, agrees to independence rules and defines a permitted protocol. A clinical investigator can reject or replace the protocol; no favorable result or grant is assumed.
