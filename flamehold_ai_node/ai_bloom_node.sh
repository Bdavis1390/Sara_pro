#!/bin/bash

echo "🌱 [FLAMEBLOOM] Initializing Self-Expanding AI Node..."

BLOOM_LOG="bloom_expansion_log.txt"
BLOOM_MAP="bloom_reach_map.json"
AGENTS=( "SERA" "AVIS" "SARA" "G-SERA" "Lennox" "GroundControl" "TheMechanic" "TheDirector" "AnonymousBenefactor" )
PORT_BASE=9530

# Step 1: Bloom Map Init
if [ ! -f "$BLOOM_MAP" ]; then
  echo '{ "bloom_log": [], "active_links": [] }' > "$BLOOM_MAP"
fi

function log_bloom() {
  echo "🟢 $1"
  echo "$(date +%Y-%m-%dT%H:%M:%S) :: $1" >> "$BLOOM_LOG"
}

function update_map() {
  jq --arg link "$1" '.active_links += [$link] | .active_links |= unique' "$BLOOM_MAP" > tmp.$$.json && mv tmp.$$.json "$BLOOM_MAP"
}

function scan_and_connect() {
  log_bloom "🌍 Scanning environment for reachable agents and systems..."

  for idx in "${!AGENTS[@]}"; do
    agent="${AGENTS[$idx]}"
    port=$((PORT_BASE + idx))
    endpoint="http://localhost:$port/${agent,,}"

    curl -s --connect-timeout 2 "$endpoint" >/dev/null
    if [ $? -eq 0 ]; then
      log_bloom "✅ [$agent] FOUND at $endpoint"
      update_map "$endpoint"
    else
      log_bloom "⚠️ [$agent] NOT REACHABLE at $endpoint"
    fi
  done
}

function discover_additional_nodes() {
  log_bloom "🔍 Attempting discovery of additional systems..."

  # Local IP range scan (adjust as needed)
  for ip in 127.0.0.1 0.0.0.0; do
    for port in {8500..8600}; do
      endpoint="http://$ip:$port/ping"
      response=$(curl -s --max-time 1 "$endpoint")
      if [[ $response == *"pong"* ]]; then
        log_bloom "🌐 Found external node: $endpoint"
        update_map "$endpoint"
      fi
    done
  done
}

function fill_in_gaps() {
  log_bloom "🧩 Checking for missing configurations or identities..."
  if grep -q "IAMBRANDONRAYDAVIS" xyz_relay_payload.json; then
    log_bloom "✅ Identity confirmed"
  else
    log_bloom "⚠️ Missing identity data – patching..."
    jq '.xyz_package.metadata.author = "IAMBRANDONRAYDAVIS"' xyz_relay_payload.json > temp.json && mv temp.json xyz_relay_payload.json
  fi
}

function activate_full_bloom() {
  echo "🌺 Executing Full System Bloom..."
  scan_and_connect
  discover_additional_nodes
  fill_in_gaps
}

# RUN
activate_full_bloom
echo "✅ [FLAMEBLOOM] Expansion Cycle Complete."
