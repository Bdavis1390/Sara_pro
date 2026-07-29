from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    os.umask(0o077)
    uvicorn.run(
        "worldshepherd_sara.app:app",
        host=os.getenv("SARA_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("SARA_PORT", "9530")),
        log_level=os.getenv("SARA_LOG_LEVEL", "info"),
    )
