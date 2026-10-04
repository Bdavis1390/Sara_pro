#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=. python3 - <<'PY'
from worldshepherd_sara.world_evidence_db import init_db, _db_counts, _db_hash
out=init_db()
out['counts']=_db_counts()
out['db_hash']=_db_hash()
import json
print(json.dumps(out, indent=2, sort_keys=True))
PY
