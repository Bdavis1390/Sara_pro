# WorldShepherd QGP/QCD metadata harvester v2

Isolated research-branch extension to Sara_pro. No modification of SARA runtime, Palace operations, or three-task scheduler.

Coverage scope: 2008–2026 literature via INSPIRE and OpenAlex. Identifiers deduplicate by DOI or arXiv with source-specific fallback. Persist provider observations, page checkpoints, source hashes, UTC timestamps, errors, query URLs, and compressed metadata in SQLite WAL.

This fetches **metadata, not full papers, private records, or detector-event datasets**. It is not comprehensive by default. Default limits: 12 remote requests, 120 seconds, minimum 3 GiB disk free, maximum 128 MiB DB footprint. Provider request budgets and publication licensing must be respected; refresh can fix pagination drift.

Dry-run: python3 harvest_qgp.py --dry-run
Safe sample: nice -n 19 python3 harvest_qgp.py --out ~/worldshepherd-research-qgp/metadata --years 2008,2014,2019,2024,2025,2026 --max-requests 12 --max-pages-per-query 1
Continue (after capacity check): nice -n 19 python3 harvest_qgp.py --out ~/worldshepherd-research-qgp/metadata --years 2008-2026 --max-requests 30 --max-pages-per-query 2

Source references: https://inspirehep.net/api/literature ; https://api.openalex.org/works ; https://hepdata.net/record/147195?format=json&light=true
Evidence gate: WS-PHYS.1.0; do not upgrade external claims from indexed literature alone.
