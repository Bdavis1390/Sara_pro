from __future__ import annotations

# Benchmark-only app target.  The production/default app remains unchanged.
# FastAPI's lifespan resolves the DurableStore global when startup executes, so
# replacing that symbol here selects the experimental store only for a Uvicorn
# process explicitly pointed at this module.
from . import app as app_module
from .persistent_audit_store import PersistentAuditDescriptorStore

app_module.DurableStore = PersistentAuditDescriptorStore
app = app_module.app
