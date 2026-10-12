# Selective Translation Revalidation

## Result from Papyri Batch 002

The second papyri re-audit produced both a positive and negative control set.

### Positive stale case
P.Tebt. 2.408:
- current source: Hipponikos;
- previous edition: Hippolitos;
- displayed translation: Hippolitos.

This remains a confirmed stale dependency.

### Negative controls
P.Oxy. 1.51:
- current source reads Isidoros;
- the apparatus preserves a different previous-edition reading;
- the displayed English uses Isidoros.

P.Oslo 2.29:
- the current source resolves Maitoytes;
- the displayed English also uses Maitoytes.

SB 14 11436:
- the revised geographic form remains semantically compatible with the displayed "Arsinoite nome".

## Consequence

A text-critical correction has three possible outcomes:

1. **CONFIRMED_STALE** — translation still reflects the superseded reading.
2. **RESOLVED_CURRENT_ON_AUDITED_CHANGE** — translation already reflects the current reading.
3. **MANUAL_REVIEW_REQUIRED** — the semantic effect cannot be safely determined automatically.

Therefore:

source_changed != translation_wrong

just as:

translation_exists != translation_current.

This is the translation-domain implementation of EIX applicability assessment.
