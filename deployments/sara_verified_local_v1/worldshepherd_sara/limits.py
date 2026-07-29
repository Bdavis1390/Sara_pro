from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

MAX_REQUEST_BYTES = 64 * 1024
MAX_SERIALIZED_BYTES = 48 * 1024
MAX_NESTING_DEPTH = 8
MAX_MAPPING_KEYS = 64
MAX_SEQUENCE_ITEMS = 128
MAX_STRING_LENGTH = 4096
MAX_AUDIT_LINE_BYTES = 64 * 1024


def validate_json_resource(value: Any) -> Any:
    """Reject JSON-shaped data that exceeds the service resource budget."""
    stack: list[tuple[Any, int]] = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_NESTING_DEPTH:
            raise ValueError(f"maximum nesting depth is {MAX_NESTING_DEPTH}")
        if isinstance(item, str):
            if len(item) > MAX_STRING_LENGTH:
                raise ValueError(f"maximum string length is {MAX_STRING_LENGTH}")
        elif isinstance(item, Mapping):
            if len(item) > MAX_MAPPING_KEYS:
                raise ValueError(f"maximum mapping size is {MAX_MAPPING_KEYS}")
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("mapping keys must be strings")
                if len(key) > MAX_STRING_LENGTH:
                    raise ValueError(f"maximum key length is {MAX_STRING_LENGTH}")
                stack.append((child, depth + 1))
        elif isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            if len(item) > MAX_SEQUENCE_ITEMS:
                raise ValueError(f"maximum sequence size is {MAX_SEQUENCE_ITEMS}")
            stack.extend((child, depth + 1) for child in item)

    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    if len(encoded) > MAX_SERIALIZED_BYTES:
        raise ValueError(f"maximum serialized size is {MAX_SERIALIZED_BYTES} bytes")
    return value
