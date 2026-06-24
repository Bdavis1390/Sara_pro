#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-$HOME/Sara_pro}"
cd "$REPO"
echo "[WORLD-INGEST] Importing ChatGPT/OpenAI export ZIPs and loose project docs into $REPO/world_documents"
python3 scripts/import_gpt_data_exports.py --repo "$REPO" --loose-projects
if [ -x scripts/world_controller_realtime_smoke_test.sh ]; then
  echo "[WORLD-INGEST] Realtime scanner smoke test available. Run it while server is running:"
  echo "  cd $REPO && ./scripts/world_controller_realtime_smoke_test.sh"
fi
echo "[WORLD-INGEST] Done. Boot UI with: cd $REPO && ./scripts/world_boot.sh"
