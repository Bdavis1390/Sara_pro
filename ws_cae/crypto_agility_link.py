"""Conservative bridge to the Crypto-Agility Manifest Internet-Draft.

This module does not compute or alter posture scores, CBOM summaries, policy,
or conformance claims. It only attaches a caller-supplied machine-verifiable
attestation URL to a caller-supplied version-1 crypto-agility manifest.
"""

from __future__ import annotations

from copy import deepcopy
from urllib.parse import urlparse


def _https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc)


def link_continuity_attestation(manifest: dict, attestation_url: str) -> dict:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if manifest.get("version") != 1:
        raise ValueError("only Crypto-Agility Manifest version 1 is supported")
    if manifest.get("manifestType") != "crypto-agility":
        raise ValueError("manifestType must be crypto-agility")
    if not _https_url(attestation_url):
        raise ValueError("attestation_url must be an absolute HTTPS URL")

    result = deepcopy(manifest)
    result["attestation"] = {"url": attestation_url}
    return result


def continuity_attestation_link(manifest: dict) -> str | None:
    attestation = manifest.get("attestation")
    if not isinstance(attestation, dict):
        return None
    url = attestation.get("url")
    if not isinstance(url, str) or not _https_url(url):
        return None
    return url
