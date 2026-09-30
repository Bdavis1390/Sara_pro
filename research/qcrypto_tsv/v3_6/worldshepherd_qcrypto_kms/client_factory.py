"""Production AWS KMS client construction helpers.

No credentials are accepted by this helper. Standard AWS credential resolution is
left to the deployment environment/IAM role. The helper enforces FIPS endpoint
resolution and disables SDK retries so one application-level Sign attempt cannot be
silently multiplied by the client retry layer.
"""
from __future__ import annotations

from typing import Any


def production_botocore_config_kwargs(region: str) -> dict[str, Any]:
    if not isinstance(region, str) or not region:
        raise ValueError("AWS region is required")
    return {
        "region_name": region,
        "use_fips_endpoint": True,
        "retries": {"total_max_attempts": 1, "mode": "standard"},
        "connect_timeout": 5,
        "read_timeout": 15,
        "tcp_keepalive": True,
        "user_agent_appid": "Worldshepherd-QCRYPTO",
    }


def build_production_kms_client(region: str):
    """Construct boto3 KMS client for a later live integration gate.

    boto3/botocore are intentionally optional dependencies in this offline candidate.
    """
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("boto3 and botocore are required for live AWS KMS integration") from exc
    config = Config(**production_botocore_config_kwargs(region))
    return boto3.client("kms", config=config)
