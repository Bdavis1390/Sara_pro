# Worldshepherd Research Intelligence Sources

This directory establishes a governed source and evidence layer for Worldshepherd/SARA without mutating the already-verified `deployments/sara_verified_local_v1` artifact.

## Current implementation

The photographed research-reference page supplied on 2026-08-09 is normalized in `research_source_registry_v1.json`. The registry now carries trust tier, access mode, collector policy, persistence policy, TTL, intended use, validation label, API documentation/base information, and required credential environment variables where applicable.

Implemented files:

- `research_source_registry_v1.json` — governed registry for all 16 reference-sheet sources.
- `load_source_registry.py` — loads the governed source registry into the existing SARA `/admin/registry` surface.
- `research_db.py` — local SQLite evidence/index store with SHA-256 deduplication, provenance fields, TTLs, rights labels, and source-level persistence enforcement.
- `source_collectors.py` — bounded Tier-1 adapters for Census, Data.gov, BLS, Library of Congress, National Archives, and Smithsonian.
- `tests/` — policy, deduplication, normalization, and secret-retention tests.
- `.github/workflows/worldshepherd-intelligence.yml` — registry validation, Python compilation, unit tests, and ephemeral database initialization.

## Load registry into SARA

From the repository root:

```bash
export SARA_ADMIN_TOKEN='use-your-existing-admin-token'
python3 intelligence/load_source_registry.py
```

The loader defaults to `http://127.0.0.1:9530`. Override with `SARA_BASE_URL` if the verified deployment is bound elsewhere. The admin token is read from the environment and is not written to disk.

## Initialize the local research database

```bash
python3 intelligence/research_db.py init
python3 intelligence/research_db.py stats
```

The default database path is `intelligence/data/worldshepherd_research.sqlite3`. Its parent directory is restricted to the current user where the operating system supports POSIX modes. API keys are never stored in the database.

## Tier-1 collectors

### Data.gov

Current Data.gov development should use the v4 Catalog API rather than the legacy CKAN integration. Automated use requires a personal api.data.gov key.

```bash
export DATAGOV_API_KEY='...'
python3 intelligence/source_collectors.py datagov 'additive manufacturing'
python3 intelligence/source_collectors.py datagov 'aerospace materials' --org-slug nasa --per-page 25
```

Data.gov records are catalog metadata. A Data.gov hit is therefore a routing signal to the originating agency dataset, not automatic validation of the underlying dataset's scientific or engineering claims.

### Census Bureau

Current 2026 Census API guidance requires an API key for data queries.

```bash
export CENSUS_API_KEY='...'
python3 intelligence/source_collectors.py census 2024 acs/acs5 \
  --get 'NAME,B01003_001E' --for 'state:*'
```

The collector stores the returned statistical response with the API key removed from all persisted provenance.

### Bureau of Labor Statistics

```bash
export BLS_REGISTRATION_KEY='...'   # optional for expanded v2 limits/features
python3 intelligence/source_collectors.py bls CES0000000001 --start-year 2024 --end-year 2026
```

BLS is treated as the machine-readable labor/statistical data path beneath the broader Department of Labor source entry.

### Library of Congress

No API key is required for the loc.gov JSON API, but rate limiting and deep-paging limits apply.

```bash
python3 intelligence/source_collectors.py loc 'directed energy deposition' --rows 25
```

Item-level rights/provenance metadata are retained when present.

### National Archives

NARA is intentionally **live-query-only** in this implementation. Current Catalog API terms state that returned API content should not be cached or stored. The source registry therefore sets `persistence_allowed: false`, and the NARA adapter prints a live response without ingesting it into SQLite.

```bash
export NARA_API_KEY='...'
python3 intelligence/source_collectors.py nara 'advanced aerospace research' --rows 25
```

Do not redirect NARA output into the Worldshepherd research database or build an automated cache around it unless the governing terms change or NARA provides explicit authorization.

### Smithsonian Open Access

```bash
export SMITHSONIAN_API_KEY='...'
python3 intelligence/source_collectors.py smithsonian 'aerospace' --rows 25
python3 intelligence/source_collectors.py smithsonian 'metallurgy' --rows 25
```

Smithsonian object metadata are retained with item-level access/rights labels where supplied. Open Access media can be followed only under the rights metadata attached to the object.

## Dry-run / inspect before ingestion

All persistent collectors support `--no-ingest`:

```bash
python3 intelligence/source_collectors.py --no-ingest loc 'energy storage'
```

This prints normalized records so the collector mapping can be reviewed before they enter SQLite.

## Source tiers

### Tier 1 — machine-readable / primary

1. U.S. Census Bureau
2. Data.gov / USA.gov
3. U.S. Department of Labor / BLS
4. Library of Congress
5. National Archives — live query only
6. Smithsonian Institution

### Tier 2 — professional / licensed

- Gallup
- ProQuest
- D&B Hoovers
- Encyclopaedia Britannica

These remain collector-disabled until authorized access and applicable license terms are explicitly configured. No access-control bypassing or subscription scraping is permitted.

### Tier 3 — discovery / context

- CNN 10
- Fact Monster
- Infoplease

These may trigger further research but cannot independently raise the maturity of an engineering, scientific, legal, medical, financial, defense, aerospace, or other mission-critical claim.

### Utility / legacy

- Convert-Me — convenience conversion reference only; critical calculations require validated constants and conversions.
- iTools Research — collector-disabled pending revalidation of current service and terms.
- CIA World Factbook — historical/archival only after its 2026 discontinuation; edition/year must travel with every retained record.

## Evidence model

Persistent research records include:

- `source_id`
- upstream identifier
- title
- canonical URL without embedded credentials
- query provenance
- `observed_at`
- `ingested_at`
- expiry/TTL
- SHA-256 of canonicalized payload
- validation label
- rights/access label
- collector version

Exact duplicate payloads from the same source are deduplicated by SHA-256. This is evidence indexing, not automatic truth assignment.

## Governance boundary

Source registration is not equivalent to validation of every claim from that source. CRE1AWS retains approval authority for high-impact use; SARA remains the governed registry/audit surface; ECHO SENTINEL LINK is the intended collection/verification layer; OVERWATCH remains the discrepancy, observability, and evidence-lineage layer.

## Next implementation gates

1. Run and clear the new intelligence CI gate on the pull request.
2. Add per-source retry/backoff and rate-limit telemetry.
3. Add a quarantine table for stale, malformed, conflicting, or rights-unclear records.
4. Add cross-source corroboration scoring without silently increasing claim maturity.
5. Add read-only research search/statistics exposure through a new SARA namespace rather than modifying the verified v1 artifact in place.
6. Add authorized adapters for Gallup, ProQuest, D&B Hoovers, and Britannica only after credentials/license scope are available.
