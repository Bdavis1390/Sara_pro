#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
LIMIT="${1:-}"
PYTHONPATH=. WORLD_MEMORY_SCAN_MAX_FILES="${LIMIT:-${WORLD_MEMORY_SCAN_MAX_FILES:-10000}}" python3 - <<'PY'
from worldshepherd_sara import world_evidence_db as m
import json, time, os
m.init_db()
roots=m._roots(None)
seen=ingested=skipped=0
started=time.time()
with m._conn() as con:
    for path in m._iter_files(roots, None):
        seen += 1
        try:
            changed, _eid = m._upsert_doc(con, path, force=False)
            if changed: ingested += 1
            else: skipped += 1
        except Exception:
            skipped += 1
    con.commit()
out={"ok": True, "roots": [str(r) for r in roots], "files_seen": seen, "files_ingested_or_changed": ingested, "files_skipped_or_deduped": skipped, "duration_sec": round(time.time()-started, 3), "counts": m._db_counts(), "db_hash": m._db_hash()}
print(json.dumps(out, indent=2, sort_keys=True))
PY
