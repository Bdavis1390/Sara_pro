# WorldShepherd QGP/QCD corpus — operational status (8 November 2026)

## Verified, completed
- 6,801 distinct indexed works spanning every year 2008–2026; 7,789 source observations; 269 successful source pages.
- 5 OpenAlex HTTP 429 records; no source data removed. An explicit provider circuit breaker now stops retries and a five-test offline suite passed.
- Source-preserving title-signal triage: 4,153 direct, 1,329 adjacent, 1,319 unclassified; NOT peer-reviewed relevance.
- Candidate project title tags (overlapping): QGP thermometry 535; plasma transport 1,094; QCD theory 1,406; field response 404; small-system studies 85; baryon junction discrimination 65.
- Date provenance: 1,767 source index-year/publication-year differences; 1,817 journal years after preprint years. These are audit signals, not errors or proof of relevance.
- All 5 CC0 STAR HEPData 147195 tables byte-matched in the GitHub mirror, and arithmetic/units consistency test passed. No detector pipeline recreation.
- 6,801 SARA *draft* review-staging records, 8,333,550 bytes, SHA-256 e5ab36c74ff27d3a14607dcb8dc450f4e8951336057ba3dfd8a6a12c14d86712. No live SARA mutation.
- Verified same-device root-partition archive: /var/tmp/worldshepherd-qgp-snapshots/qgp_corpus_20261108T200223Z.tar.gz (7,677,851 bytes; SHA-256 5a30e93dc6682b7456577578fd170e574738214a9455be2e420a93e15248b709). This is **not** an off-device or cloud backup.
- New scripts: screen_relevance.py, audit_dates.py, snapshot_corpus.py, test_harvest.py, plus existing harvester, SARA adapter, DOI pinning and HEPData validation.
- No fourth scheduled task, no modification to Palace original 54-case campaign, no production branch merge.

## Next scientific gates
1. Validate titles and abstracts in the top-weighted QGP subset; flag retractions and corrections separately.
2. Continue topic/year/provider partition coverage; do not infer completeness from 269 pages. Respect OpenAlex 429 and cursor paging key restrictions.
3. Reproduce STAR spectral extraction using published backgrounds, fit ranges, and covariance; do not conflate with table consistency.
4. Build defensible model comparisons on baryon-junction and non-Gaussian transport hypotheses; obtain independent expert review.
5. Establish independent off-device storage of the locally generated SQLite, staging and QA results before retaining terabyte-scale source data.
6. Preserve WS-PHYS.1.0 evidence categories and the original 18-dissertation program. Physical coupling claims require controlled experiment, not bibliometric correlation.

## Technical hazards to track
- Result drift and pagination boundaries; a fixed page size is now enforced for each database.
- DOI and arXiv fallback records may not always coalesce.
- Provider publication year versus earliest preprint year must be retained separately.
- Keyword searches return false positives and miss relevant papers.
- Both Lenovo partitions reside on one physical eMMC, so local snapshots do not mitigate total-device loss.
