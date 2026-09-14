from __future__ import annotations

import math
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable validation-error value.

    FastAPI validation errors may retain rejected input values. If those values
    contain NaN/Infinity, Starlette's strict JSON response encoder can itself
    fail while trying to return the intended 422. This sanitizer preserves the
    diagnostic structure while replacing non-finite floats and exception
    objects with bounded strings.
    """
    if isinstance(value, float):
        return value if math.isfinite(value) else "<non-finite-number>"
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


async def sanitized_request_validation_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": _json_safe(exc.errors())},
    )
