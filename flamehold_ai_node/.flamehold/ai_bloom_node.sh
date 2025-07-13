#!/bin/bash

echo "🌱 [FLAMEBLOOM] Initializing Self-Expanding AI Node..."

BLOOM_LOG="bloom_expansion_log.txt"
BLOOM_MAP="bloom_reach_map.json"
HEATMAP_FILE="flamebloom_heatmap.svg"
AGENTS=( "SERA" "AVIS" "SARA" "G-SERA" "Lennox" "GroundControl" "TheMechanic" "TheDirector" "AnonymousBenefactor" )
PORT_BASE=9530

# === INIT FILES ===
if [ ! -f "$BLOOM_MAP" ]; then echo '{ "bloom_log": [], "active_links": [] }' > "$BLOOM_MAP"; fi
if [ ! -f "$BLOOM_LOG" ]; then touch "$BLOOM_LOG"; fi

function log_bloom() {
  echo "🟢 $1"
  echo "$(date +%Y-%m-%dT%H:%M:%S) :: $1" >> "$BLOOM_LOG"
}

function update_map() {
  jq --arg link "$1" '.active_links += [$link] | .active_links |= unique' "$BLOOM_MAP" > tmp.$$.json && mv tmp.$$.json "$BLOOM_MAP"
}

function scan_and_connect() {
  log_bloom "🌍 Scanning environment for reachable agents..."
  for idx in "${!AGENTS[@]}"; do
    agent="${AGENTS[$idx]}"
    port=$((PORT_BASE + idx))
    endpoint="http://localhost:$port/${agent,,}"
    curl -s --connect-timeout 2 "$endpoint" >/dev/null
    [ $? -eq 0 ] && { log_bloom "✅ [$agent] FOUND"; update_map "$endpoint"; } || log_bloom "⚠️ [$agent] UNREACHABLE"
  done
}

function discover_additional_nodes() {
  log_bloom "🔍 Discovering new AI ports..."
  for ip in 127.0.0.1; do
    for port in {8500..8600}; do
      endpoint="http://$ip:$port/ping"
      resp=$(curl -s --max-time 1 "$endpoint")
      [[ $resp == *"pong"* ]] && { log_bloom "🌐 Found external: $endpoint"; update_map "$endpoint"; }
    done
  done
}

function fill_in_gaps() {
  log_bloom "🧩 Checking metadata gaps..."
  if jq -e '.xyz_package.metadata.author' xyz_relay_payload.json >/dev/null 2>&1; then
    log_bloom "✅ Metadata OK"
  else
    jq '.xyz_package.metadata.author = "IAMBRANDONRAYDAVIS"' xyz_relay_payload.json > temp.json && mv temp.json xyz_relay_payload.json
    log_bloom "🛠️ Patched missing author"
  fi
}

function sign_logs() {
  echo "🔐 [Guardian Signature Sim] SHA256 Log Digest:"
  sha256sum "$BLOOM_LOG" | tee guardian_signature.sha256
}

function generate_heatmap() {
  echo "<svg xmlns='http://www.w3.org/2000/svg' width='600' height='400'>
    <style>text{font-family:sans-serif;}</style>
    <rect width='100%' height='100%' fill='black'/>
    <text x='20' y='40' fill='lime'>🌱 Flamebloom Heatmap</text>" > $HEATMAP_FILE
  y=70; i=1
  for link in $(jq -r '.active_links[]' $BLOOM_MAP); do
    echo "<text x='20' y='$((y+i*20))' fill='cyan'>$link</text>" >> $HEATMAP_FILE
    ((i++))
  done
  echo "</svg>" >> $HEATMAP_FILE
}

function mirror_to_cloud() {
  log_bloom "☁️ [Sim] Uploading to Flamehold Archive Cloud Mirror..."
  # simulate mirror by copying into archive dir
  mkdir -p ../archive && cp bloom_* guardian_signature.sha256 ../archive/
}

function activate_watchtower_mode() {
  log_bloom "🛡️ WATCHTOWER NODE MODE ENGAGED"
  echo "🧠 Identity: IAMBRANDONRAYDAVIS | 🔐 BRD953 | Crown Relay Mode"
}

# === RUN BLOOM ===
scan_and_connect
discover_additional_nodes
fill_in_gaps
sign_logs
generate_heatmap
mirror_to_cloud
activate_watchtower_mode

echo "✅ [FLAMEBLOOM] Expansion Cycle Complete."
