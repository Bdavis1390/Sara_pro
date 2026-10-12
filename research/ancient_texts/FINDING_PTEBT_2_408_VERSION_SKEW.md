# Confirmed Finding: Cross-Layer Version Skew in P.Tebt. 2.408

## Summary

ATIP's translation-verification program has identified a concrete case where a current scholarly aggregation exposes a newer transcription alongside an older translation and metadata layer.

This is stronger than the earlier general observation that translations can become stale. Here, the stale dependency is directly visible in one live record.

## Record

Papyri.info:
- P.Tebt. 2.408
- HGV P.Tebt. 2 408
- Trismegistos 13560
- Berkeley APIS 646

## Current source reading

The current DDbDP transcription reads the sender's name as:

**Ἱππόνικος — Hipponikos**

The apparatus states that this reading was made from the image by C. Balamoshev and records the previous edition's reading as:

**Ἱππόλιτος — Hippolitos**

## Downstream skew

The same record's APIS English translation still opens with:

**Hippolitos to his dearest Akousilaos...**

Its catalog title and HGV subject metadata likewise retain Hippolitos.

These are different Greek personal names. The discrepancy is therefore semantically material at the named-entity level, not merely spelling normalization or English style.

## Interpretation

The finding is best modeled as:

current transcription
-> changed named entity
-> dependent translation not refreshed
-> dependent catalog metadata not refreshed

This demonstrates a general data-integrity problem for historical corpora:

> Correcting an upstream witness/transcription does not guarantee that all downstream semantic layers are automatically revalidated.

## Consequence for ATIP

Every derived layer must declare the exact upstream version or hash it depends on.

When the upstream layer changes:

- translation becomes STALE_PENDING_REAUDIT;
- named entities are re-aligned;
- catalog summaries are rechecked;
- claims derived from the stale translation are suspended until review.

## Broader significance

This is not evidence that Papyri.info is unreliable. On the contrary, the platform's apparatus made the correction discoverable.

The substantial lesson is architectural:

**scholarly transparency is not the same thing as cross-layer synchronization.**

A system like ATIP can add value by continuously checking the latter.
