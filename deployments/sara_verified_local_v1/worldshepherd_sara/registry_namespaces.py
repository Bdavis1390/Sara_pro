from __future__ import annotations


# Keep registry namespace identifiers in a dependency-free module so the core
# SARA application can protect governed namespaces without importing optional
# integration implementations or their network-facing dependencies.
DISCORD_RECEIPTS_REGISTRY_KEY = "SARA_DISCORD_NOTIFICATION_RECEIPTS"
