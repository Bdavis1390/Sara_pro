# WS-CAE witness hardening checkpoint

Status: OPEN / defensive validation follow-up.

The manifest, transition, transparency, and SCITT continuity paths now fail closed on canonical lowercase SHA-256 content identifiers and timezone-aware timestamps where applicable.

`ws_cae/continuity_witness.py` still accepts witness receipt roots using a prefix-only `sha256:` shape check and accepts any non-empty `observed_at` string. Before treating witness quorum metadata as standards-grade, align witness validation with `ws_cae.continuity_validation.valid_content_id` and `valid_datetime`, and add regression tests for malformed roots, uppercase digest aliases, impossible timestamps, and timezone-less observations.

This is a metadata-integrity issue only. It does not imply a cryptocurrency exploit, asset loss, or compromise.
