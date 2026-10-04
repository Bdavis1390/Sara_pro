#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:9530"
OUT="logs/world_memory_validation_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUT"

ADMIN_TOKEN="$(grep '^SARA_ADMIN_TOKEN=' .env | cut -d= -f2- || true)"

if [ -z "$ADMIN_TOKEN" ]; then
  echo "[WORLD] ERROR: SARA_ADMIN_TOKEN not found in .env"
  echo "[WORLD] Check with: grep '^SARA_ADMIN_TOKEN=' .env"
  exit 1
fi

echo "[WORLD] Validation output folder: $OUT"
echo "[WORLD] Admin token loaded."

request_json() {
  local method="$1"
  local name="$2"
  local url="$3"
  local outfile="$OUT/$name.json"
  local header_file="$OUT/$name.headers"
  local status

  echo
  echo "[$name] $method $url"

  if [ "$method" = "GET_PUBLIC" ]; then
    status="$(curl -sS -D "$header_file" -o "$outfile" -w "%{http_code}" "$url" || true)"
  elif [ "$method" = "GET" ]; then
    status="$(curl -sS -D "$header_file" -o "$outfile" -w "%{http_code}" \
      -H "X-SARA-ADMIN-TOKEN: $ADMIN_TOKEN" \
      "$url" || true)"
  elif [ "$method" = "POST" ]; then
    status="$(curl -sS -D "$header_file" -o "$outfile" -w "%{http_code}" \
      -X POST \
      -H "X-SARA-ADMIN-TOKEN: $ADMIN_TOKEN" \
      "$url" || true)"
  else
    echo "[WORLD] ERROR: unsupported method $method"
    exit 1
  fi

  echo "[HTTP] $status"

  if [ "$status" -lt 200 ] || [ "$status" -ge 300 ]; then
    echo "[WORLD] ERROR: request failed for $name"
    echo "[WORLD] Headers:"
    cat "$header_file"
    echo
    echo "[WORLD] Body:"
    cat "$outfile"
    echo
    exit 1
  fi

  python3 -m json.tool "$outfile"
}

request_json "GET_PUBLIC" "01_health" "$BASE/health"
request_json "GET" "02_world_status" "$BASE/world/status"
request_json "POST" "03_memory_init" "$BASE/world/memory/init"
request_json "GET" "04_memory_stats" "$BASE/world/memory/stats"
request_json "GET" "05_memory_search_worldshepherd" "$BASE/world/memory/search?q=Worldshepherd"
request_json "GET" "06_memory_projects" "$BASE/world/memory/projects"
request_json "GET" "07_memory_timeline" "$BASE/world/memory/timeline"
request_json "GET" "08_memory_verify" "$BASE/world/memory/verify"

echo
echo "[WORLD] Running smoke suites..."
if [ -x ./scripts/world_controller_realtime_smoke_test.sh ]; then
  ./scripts/world_controller_realtime_smoke_test.sh | tee "$OUT/09_realtime_smoke.txt"
else
  echo "[WORLD] realtime smoke suite not tracked; skipping optional legacy smoke" | tee "$OUT/09_realtime_smoke.txt"
fi
./scripts/world_ingest_all_evidence_db.sh | tee "$OUT/10_ingest.json"
./scripts/world_evidence_db_smoke_test.sh | tee "$OUT/11_evidence_db_smoke.txt"

echo
echo "[WORLD] Validation complete."
echo "[WORLD] Results saved in: $OUT"
