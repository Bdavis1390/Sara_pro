# Worldshepherd Research Intelligence Sources

This directory establishes a governed source layer for Worldshepherd/SARA.

## Purpose

The photographed research-reference page supplied on 2026-08-09 has been normalized into `research_source_registry_v1.json`. The registry does not treat all sources as equal. Each source is assigned a trust tier, access mode, collector policy, TTL, intended use, and default validation label before data enters SARA/ECHO SENTINEL LINK.

## Load into SARA

`load_source_registry.py` patches the full governed registry into SARA under the top-level key `research_source_registry` using the existing authenticated `/admin/registry` endpoint. SARA's current implementation records a `registry_patched` audit event after a successful patch.

Example from the repository root:

```bash
export SARA_ADMIN_TOKEN='use-your-existing-admin-token'
python3 intelligence/load_source_registry.py
```

The loader defaults to `http://127.0.0.1:9530`. Override with `SARA_BASE_URL` if the verified deployment is bound elsewhere. The script reads the admin token from the environment, does not write it to disk, validates duplicate source IDs, verifies the returned source count, and exits nonzero on an HTTP or validation failure.

## Ingestion order

### Tier 1 — machine-readable / primary

1. U.S. Census Bureau — demographics, geography, business/economic baselines, ACS and market sizing.
2. Data.gov / USA.gov — cross-agency federal dataset discovery and open-data feeds.
3. U.S. Department of Labor — workforce, labor-market and earnings context; prefer DOL/BLS machine-readable datasets.
4. Library of Congress — catalog metadata, maps, legislation, digitized primary sources and authority records.
5. National Archives — federal records, declassified material and archival provenance.
6. Smithsonian Institution — scientific collections, research datasets, technology history, natural-history and 3D/open-access assets.

These are the first candidates for bounded collectors because they are authoritative public sources and often expose machine-readable interfaces.

### Tier 2 — professional / licensed

- Gallup
- ProQuest
- D&B Hoovers
- Encyclopaedia Britannica

These may substantially improve market, public-opinion, literature, company, partner and historical research, but collection must remain inside authorized subscriptions/APIs and applicable terms. Do not bypass access controls.

### Tier 3 — discovery / context

- CNN 10
- Fact Monster
- Infoplease

Use for topic discovery, current-events orientation, terminology and low-risk cross-checking. Do not use as the sole evidence base for engineering, scientific, legal, medical, financial, defense, aerospace or other mission-critical claims.

### Utility / legacy

- Convert-Me: convenience conversion and historical/exotic-unit reference only. Mission calculations require independently validated constants and unit conversions.
- iTools Research: retained as a legacy discovery source but collector-disabled until current operation and terms are revalidated.
- CIA World Factbook: retained as historical/archival data only. The CIA discontinued publication in 2026; every imported record must retain edition/year and must not be represented as current.

## Required normalized event fields

Every ingested record should preserve at least:

- `source_id`
- upstream record/page/dataset identifier
- original URL
- `observed_at`
- `ingested_at`
- subject/domain tags
- location and precision when applicable
- confidence
- corroboration state
- evidence/content hash
- handling label
- validation label
- expiry/TTL
- collector name/version
- rights/license/access metadata when relevant

## Governance boundary

Source registration is not equivalent to validation of every claim from that source. Data are evidence inputs. CRE1AWS retains approval authority for high-impact use; SARA records provenance and audit state; ECHO SENTINEL LINK performs collection/verification; OVERWATCH records observability, discrepancies and evidence lineage.

## Next implementation gates

1. Add a schema validator for `research_source_registry_v1.json`.
2. Add read-only source-registry exposure to the SARA API.
3. Implement bounded collectors for Census, Data.gov, LOC, NARA and Smithsonian first.
4. Add per-source rate limits, cache/TTL and retry policy.
5. Add provenance hashes and append-only ingestion audit events.
6. Add a quarantine queue for conflicting, stale, malformed or rights-unclear records.
7. Add manual/authorized ingestion adapters for Gallup, ProQuest, D&B Hoovers and Britannica.
8. Add cross-source corroboration scoring so tertiary sources can trigger research without silently raising claim maturity.
