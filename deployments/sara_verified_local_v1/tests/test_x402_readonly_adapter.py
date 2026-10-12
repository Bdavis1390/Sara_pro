from __future__ import annotations

import json

import pytest

from worldshepherd_sara.x402_readonly_adapter import (
    MAX_SUPPORTED_RESPONSE_BYTES,
    USER_AGENT,
    X402_ALLOWED_NETWORK,
    X402_ALLOWED_SCHEME,
    X402_ALLOWED_VERSION,
    X402ReadOnlyAdapterError,
    capability_sha256,
    fetch_supported,
    validate_supported_response,
)


def supported_payload():
    return {
        "kinds": [
            {
                "x402Version": 2,
                "scheme": "exact",
                "network": "eip155:8453",
            },
            {
                "x402Version": 2,
                "scheme": "exact",
                "network": "eip155:84532",
            },
        ],
        "extensions": ["builder-code"],
    }


class FakeResponse:
    def __init__(self, payload, *, status=200):
        self.status = status
        self._payload = payload

    def read(self, _limit):
        if isinstance(self._payload, bytes):
            return self._payload
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_validator_selects_only_approved_base_sepolia_exact_v2():
    capability = validate_supported_response(supported_payload())

    assert capability.version == X402_ALLOWED_VERSION
    assert capability.scheme == X402_ALLOWED_SCHEME
    assert capability.network == X402_ALLOWED_NETWORK
    assert len(capability.capability_sha256) == 64


def test_mainnet_only_advertisement_fails_closed():
    with pytest.raises(X402ReadOnlyAdapterError, match="Base Sepolia"):
        validate_supported_response(
            {
                "kinds": [
                    {
                        "x402Version": 2,
                        "scheme": "exact",
                        "network": "eip155:8453",
                    }
                ]
            }
        )


def test_wrong_version_or_scheme_does_not_auto_promote():
    with pytest.raises(X402ReadOnlyAdapterError, match="Base Sepolia"):
        validate_supported_response(
            {
                "kinds": [
                    {
                        "x402Version": 1,
                        "scheme": "exact",
                        "network": "eip155:84532",
                    },
                    {
                        "x402Version": 2,
                        "scheme": "upto",
                        "network": "eip155:84532",
                    },
                ]
            }
        )


def test_capability_digest_is_semantic_and_stable():
    first = {
        "x402Version": 2,
        "scheme": "exact",
        "network": "eip155:84532",
        "extra": {"ignored": "transport-specific"},
    }
    second = {
        "network": "eip155:84532",
        "scheme": "exact",
        "x402Version": 2,
    }

    assert capability_sha256(first) == capability_sha256(second)


def test_fetch_is_get_only_has_no_credentials_and_uses_bounded_endpoint():
    observed = {}

    def opener(request, *, timeout):
        observed["method"] = request.get_method()
        observed["url"] = request.full_url
        observed["headers"] = dict(request.header_items())
        observed["timeout"] = timeout
        return FakeResponse(supported_payload())

    capability = fetch_supported(opener=opener, timeout=7.0)

    assert capability.network == "eip155:84532"
    assert observed["method"] == "GET"
    assert observed["url"] == "https://x402.org/facilitator/supported"
    assert observed["timeout"] == 7.0
    headers = {key.lower(): value for key, value in observed["headers"].items()}
    assert headers["user-agent"] == USER_AGENT
    assert "authorization" not in headers
    assert "payment-signature" not in headers


def test_non_200_fails_closed():
    def opener(_request, *, timeout):
        assert timeout == 15.0
        return FakeResponse({}, status=403)

    with pytest.raises(X402ReadOnlyAdapterError, match="HTTP 403"):
        fetch_supported(opener=opener)


def test_malformed_json_fails_closed():
    def opener(_request, *, timeout):
        assert timeout == 15.0
        return FakeResponse(b"{not-json")

    with pytest.raises(X402ReadOnlyAdapterError, match="valid JSON"):
        fetch_supported(opener=opener)


def test_oversized_response_fails_closed():
    class OversizedResponse(FakeResponse):
        def read(self, _limit):
            return b"x" * (MAX_SUPPORTED_RESPONSE_BYTES + 1)

    def opener(_request, *, timeout):
        assert timeout == 15.0
        return OversizedResponse({})

    with pytest.raises(X402ReadOnlyAdapterError, match="bounded size"):
        fetch_supported(opener=opener)
