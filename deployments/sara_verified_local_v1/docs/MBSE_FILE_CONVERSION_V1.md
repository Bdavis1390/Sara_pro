# Worldshepherd File-Backed MBSE Conversion v1

Status: **candidate synthetic software demonstrator** supporting issue #18.

## Why this exists

The original `WS-MBSE-SYNTH-001` benchmark proved that a conservative rule set could recover a frozen graph from already loaded Python/JSON artifact objects. That is useful internal evidence, but it does not by itself demonstrate a file-to-model conversion path.

External teaming feedback sharpened the Phase-I boundary: first demonstrate conversion of relevant legacy artifacts; provenance/bookkeeping enhancements should not substitute for the core conversion capability.

This candidate therefore moves one bounded step closer to that requirement:

```text
separate source files
    -> safe file ingest + SHA-256 custody
    -> supported TXT/CSV/JSON parsing
    -> conservative entity/relationship extraction
    -> provenance-bearing Evidence Graph
    -> Worldshepherd neutral system model
    -> frozen ground-truth scoring + retained negative evidence
```

## Frozen corpus

`fixtures/mbse_file_corpus_v1/manifest.json` defines synthetic fixture `WS-MBSE-FILE-SYNTH-002`.

The source corpus is deliberately file-backed and heterogeneous:

- `technical_manual.txt` — synthetic prose technical-manual excerpt;
- `hardware_bom.csv` — synthetic hardware BOM;
- `network_configuration.json` — synthetic host/service/consumer configuration;
- `cable_record.csv` — synthetic power cable record.

Every manifest source has a predeclared SHA-256 digest. The loader recomputes the digest before extraction and fails closed on mismatch.

The corpus is synthetic and contains no AEGIS, Navy, partner, proprietary, CUI, or classified source material.

## Security / source-custody behavior

The file loader:

- resolves source paths beneath the manifest directory;
- rejects `..`/absolute-path escape after resolution;
- accepts only supported `.txt`, `.md`, `.csv`, and `.json` files;
- requires UTF-8 text;
- verifies an expected SHA-256 when the manifest supplies one;
- rejects duplicate artifact IDs;
- validates row-oriented versus text-oriented source structure before extraction.

These controls establish source custody for this bounded software path. They do not establish government data-handling authorization or classified/CUI readiness.

## Conversion behavior

The current extraction engine remains intentionally conservative.

Supported semantics in the frozen family include:

- explicit 28 VDC `powers` relationships from supported prose/cable patterns;
- explicit sensor-to-processor Ethernet-data relationship from the frozen prose pattern;
- host-to-service `hosts` relationships from structured network rows;
- service-to-consumer `publishes_track_data` relationships from structured network rows;
- entity identity/type/part metadata from the BOM where explicitly supplied.

The candidate graph retains source references plus source file path, SHA-256, and byte count in node/edge provenance attributes.

## Output

`run_file_backed_conversion()` produces:

- source-artifact evidence;
- a candidate Evidence Graph;
- a canonical Worldshepherd neutral model;
- entity/relationship precision and recall against frozen ground truth;
- unsupported and missed entities/relationships;
- explicit claims boundaries;
- a deterministic output digest.

## What this closes

If the exact-head tests pass, this can support a narrow statement such as:

> `IMPLEMENTED IN SOFTWARE / PROVEN INTERNALLY` for deterministic conversion of the exact frozen synthetic TXT/CSV/JSON fixture family into a provenance-bearing Worldshepherd neutral model.

It would strengthen evidence that the pipeline accepts separate legacy-like files rather than only preconstructed in-memory objects.

## What this does **not** close

This candidate does not establish:

- general document understanding;
- OCR;
- PDF parsing or semantic recovery from arbitrary PDFs;
- image/diagram understanding;
- arbitrary spreadsheet/workbook parsing;
- robust NLP across unknown technical-manual language;
- requirement/configuration-document generalization beyond supported patterns;
- automatic SysML reconstruction;
- valid SysML/XMI serialization;
- Cameo/MagicDraw import compatibility;
- AEGIS/Navy data reconstruction;
- Secret/CUI/classified processing authority;
- production reconstruction accuracy;
- government evaluation or acceptance.

`neutral_model.export_sysml_xmi_stub()` therefore remains deliberately unimplemented. It should not be replaced with a nominal XML file merely to claim “XMI export.” An authoritative target metamodel/tool import path must be selected and tested first.

## Next technical gates

1. Add synthetic requirements/configuration artifacts with unseen phrasing and score held-out generalization rather than only the frozen known phrases.
2. Add a bounded PDF text-extraction lane only with a pinned parser and source-page provenance; image-only documents remain a separate OCR/vision problem.
3. Add diagram/image extraction as its own measured lane rather than treating file acceptance as semantic understanding.
4. Define a target modeling interoperability contract from authoritative SysML/tool documentation.
5. Export only the subset actually represented by that contract and test round-trip/import behavior in an appropriate tool/environment.
6. Move provenance/bookkeeping sophistication into the Phase-II expansion path after conversion feasibility is independently credible.

## Falsification

The candidate fails its own bounded claim if any frozen source digest mismatch is silently accepted, path escape succeeds, extracted relationships lose source evidence, unsupported inference appears, ground-truth content is missed beyond the declared thresholds, or repeated execution over identical frozen inputs changes the output digest.
