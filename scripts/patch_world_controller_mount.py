#!/usr/bin/env python3
"""Best-effort FastAPI mount patcher for WORLD CONTROLLER."""
from pathlib import Path

ROOT = Path.cwd()
IMPORT_LINE = "from worldshepherd_sara.world_controller import router as world_controller_router\n"
INCLUDE_LINE = "app.include_router(world_controller_router)\n"

candidates = []
for path in (ROOT / "worldshepherd_sara").rglob("*.py"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "FastAPI(" in text and "app" in text:
        candidates.append(path)

if not candidates:
    print("ERROR: Could not find a FastAPI app file under worldshepherd_sara/.")
    print("Manually add:")
    print(IMPORT_LINE.rstrip())
    print(INCLUDE_LINE.rstrip())
    raise SystemExit(1)

path = candidates[0]
text = path.read_text(encoding="utf-8")
if "world_controller_router" in text:
    print(f"Already mounted or imported in {path}")
    raise SystemExit(0)

lines = text.splitlines(keepends=True)
insert_import_at = 0
for idx, line in enumerate(lines):
    if line.startswith("from ") or line.startswith("import "):
        insert_import_at = idx + 1
lines.insert(insert_import_at, IMPORT_LINE)
text = "".join(lines)

# Place include after the first app = FastAPI(...) line if it is one-line; otherwise append near end.
lines = text.splitlines(keepends=True)
inserted = False
for idx, line in enumerate(lines):
    if "FastAPI(" in line and "=" in line and line.rstrip().endswith(")"):
        lines.insert(idx + 1, INCLUDE_LINE)
        inserted = True
        break
if not inserted:
    lines.append("\n# WORLD CONTROLLER mount\n")
    lines.append(INCLUDE_LINE)

backup = path.with_suffix(path.suffix + ".bak_world_controller")
backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
path.write_text("".join(lines), encoding="utf-8")
print(f"Mounted WORLD CONTROLLER in {path}")
print(f"Backup written to {backup}")
