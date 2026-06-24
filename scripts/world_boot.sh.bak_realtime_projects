#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-$HOME/Sara_pro}"
NEXT_ZIP="$(ls -t "$HOME"/Downloads/world_controller_next_actions_patch*.zip 2>/dev/null | head -n1 || true)"
EVIDENCE_ZIP="$(ls -t "$HOME"/Downloads/world_controller_evidence_links_patch*.zip 2>/dev/null | head -n1 || true)"
DOSSIER_ZIP="$(ls -t "$HOME"/Downloads/world_controller_dossier_ui_patch*.zip 2>/dev/null | head -n1 || true)"
FULL_ZIP="$(ls -t "$HOME"/Downloads/world_controller_full_controls_patch*.zip 2>/dev/null | head -n1 || true)"
BASE_ZIP="$(ls -t "$HOME"/Downloads/world_controller_build_package*.zip 2>/dev/null | head -n1 || true)"

echo "[WORLD] Repo: $REPO"
cd "$REPO"

install_zip() {
  local zip="$1" tmp="$2" inner="$3" script="$4" label="$5"
  echo "[WORLD] Installing $label from: $zip"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  unzip -o "$zip" -d "$tmp" >/dev/null
  bash "$tmp/$inner/scripts/$script" "$REPO"
}

if [ -n "$NEXT_ZIP" ]; then
  install_zip "$NEXT_ZIP" /tmp/world_controller_next_actions_patch world_controller_next_actions_patch install_world_controller_next_actions.sh "NEXT-ACTIONS CONTROLS"
elif grep -q '@router.get("/preflight")' "$REPO/worldshepherd_sara/world_controller.py" 2>/dev/null; then
  echo "[WORLD] Next-actions controls already present."
elif [ -n "$EVIDENCE_ZIP" ]; then
  install_zip "$EVIDENCE_ZIP" /tmp/world_controller_evidence_links_patch world_controller_evidence_links_patch install_world_controller_evidence_links.sh "EVIDENCE LINKS"
elif [ -n "$DOSSIER_ZIP" ]; then
  install_zip "$DOSSIER_ZIP" /tmp/world_controller_dossier_ui_patch world_controller_dossier_ui_patch install_world_controller_dossier_ui.sh "DOSSIER UI"
elif [ -n "$FULL_ZIP" ]; then
  install_zip "$FULL_ZIP" /tmp/world_controller_full_controls_patch world_controller_full_controls_patch install_world_controller_full_controls.sh "FULL CONTROLS"
elif [ -n "$BASE_ZIP" ]; then
  install_zip "$BASE_ZIP" /tmp/world_controller_build world_controller_build_package install_world_controller.sh "BASE CONTROLS"
else
  echo "[WORLD] WARNING: no WORLD CONTROLLER package zip found in ~/Downloads."
  echo "[WORLD] Continuing with existing repo files."
fi

if [ ! -f "$REPO/.env" ] && [ -f "$REPO/.env.example" ]; then
  cp "$REPO/.env.example" "$REPO/.env"
elif [ ! -f "$REPO/.env" ]; then
  touch "$REPO/.env"
fi
if ! grep -q '^SARA_ADMIN_TOKEN=' "$REPO/.env"; then
  echo "SARA_ADMIN_TOKEN=change-me-admin-token" >> "$REPO/.env"
fi

echo "[WORLD] Verifying next-actions route..."
grep -n '@router.get("/preflight")' "$REPO/worldshepherd_sara/world_controller.py" >/dev/null || {
  echo "[WORLD] WARNING: /world/preflight route missing. UI may be older than next-actions build."
}

echo "[WORLD] Compiling Python..."
python3 -m compileall worldshepherd_sara >/dev/null

echo
echo "[WORLD] Boot targets:"
echo "  Legacy UI: http://127.0.0.1:9530/ui"
echo "  WORLD UI:  http://127.0.0.1:9530/world/ui"
echo

if [ -x "$REPO/scripts/start_interface.sh" ]; then
  exec "$REPO/scripts/start_interface.sh"
else
  echo "[WORLD] ERROR: scripts/start_interface.sh not found or not executable."
  exit 1
fi
