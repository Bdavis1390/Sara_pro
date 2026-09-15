from __future__ import annotations

from typing import Any

from .audit_checkpoint import (
    SaraAuditCheckpointError,
    SaraAuditCheckpointManager,
)


class GuardedSaraAuditCheckpointManager(SaraAuditCheckpointManager):
    """Operational checkpoint manager that verifies history before extension.

    The base manager already signs an order-sensitive complete audit prefix and
    verifies it on demand.  This guarded variant additionally requires the
    latest existing signed prefix to verify *before* any subsequent checkpoint
    can be created.  The check and extension execute while holding the same
    re-entrant checkpoint/store locks, so another local append cannot slip
    between verification and checkpoint creation.
    """

    def create_checkpoint(self) -> dict[str, Any]:
        with self._checkpoint_lock, self.store._lock:
            if self.ledger_path.exists():
                status = self.verify_current()
                if status.get("status") not in {
                    "PASS",
                    "PASS_WITH_UNCHECKPOINTED_TAIL",
                }:
                    raise SaraAuditCheckpointError(
                        "existing SARA audit checkpoint state is not extendable"
                    )
            return super().create_checkpoint()
