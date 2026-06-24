#!/usr/bin/env bash
set -euo pipefail
REPO="${1:-$HOME/Sara_pro}"
CANONICAL="$REPO/worldshepherd_sara/world_controller_static/index.dossier.html"
TARGET="$REPO/worldshepherd_sara/world_controller_static/index.html"
if [ -f "$CANONICAL" ]; then
  cp "$CANONICAL" "$TARGET"
  echo "[WORLD-DOSSIER] Dossier UI applied."
else
  echo "[WORLD-DOSSIER] WARNING: canonical dossier UI missing: $CANONICAL" >&2
fi
