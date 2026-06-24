# WORLD CONTROLLER Build Guide

## Purpose

WORLD CONTROLLER is the local-first, simulate-first command surface for Worldshepherd SARA / SSPADAWANZZ.

It adds:

- `/world/ui` browser console
- `/world/status`
- `/world/registry`
- `/world/command/parse`
- `/world/command/simulate`
- `/world/command/execute`
- `/world/audit`

## Safety model

Commands pass through:

```text
Command -> Guardian classification -> Oracle simulation -> Sentinel check -> Ark restore ID -> Audit record
```

Default execution rules:

- GREEN/BLUE can execute only with `execute_confirm=true`
- AMBER requires `WORLD_ALLOW_AMBER_EXECUTE=1` and confirmation
- RED/BLACK are denied by default
- No external side effects are performed in this first controller shell

## Install

Run from repo root:

```bash
./scripts/install_world_controller.sh ~/Sara_pro
cd ~/Sara_pro
python scripts/patch_world_controller_mount.py
python -m compileall worldshepherd_sara
```

Start the interface:

```bash
./scripts/start_interface.sh
```

Open:

```text
http://127.0.0.1:9530/world/ui
```

Smoke test:

```bash
./scripts/world_controller_smoke_test.sh
```

## Manual mount fallback

Find the file where your FastAPI app is created, then add:

```python
from worldshepherd_sara.world_controller import router as world_controller_router
app.include_router(world_controller_router)
```

Restart the service after editing.
