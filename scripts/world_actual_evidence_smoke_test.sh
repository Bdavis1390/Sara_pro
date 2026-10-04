#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:9530}"
ADMIN_TOKEN="${ADMIN_TOKEN:-$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2-)}"

echo "[1] Evidence index"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN_TOKEN" "$BASE/world/evidence" >/dev/null

echo "[2] Evidence API search"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN_TOKEN" "$BASE/world/evidence/api/search?q=Worldshepherd" | python3 -m json.tool >/dev/null

echo "[3] Evidence source sample"
SID="$(python3 - <<'PY'
import os, sqlite3
from pathlib import Path
p=Path(os.environ.get('WORLD_EVIDENCE_DB', 'data/world_evidence.db'))
con=sqlite3.connect(p); con.row_factory=sqlite3.Row
r=con.execute('select id from sources order by id desc limit 1').fetchone()
print(r['id'] if r else 1)
PY
)"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN_TOKEN" "$BASE/world/evidence/source/$SID" >/dev/null

echo "[4] Evidence record sample"
EID="$(python3 - <<'PY'
import os, sqlite3
from pathlib import Path
p=Path(os.environ.get('WORLD_EVIDENCE_DB', 'data/world_evidence.db'))
con=sqlite3.connect(p); con.row_factory=sqlite3.Row
r=con.execute('select id from evidence order by id desc limit 1').fetchone()
print(r['id'] if r else 1)
PY
)"
curl -fsS -H "X-SARA-ADMIN-TOKEN: $ADMIN_TOKEN" "$BASE/world/evidence/evidence/$EID" >/dev/null

echo "WORLD CONTROLLER actual evidence links smoke test passed"
