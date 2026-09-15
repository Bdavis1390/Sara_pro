from __future__ import annotations

from pathlib import Path


SOURCE_TARGET = '"worldshepherd_sara.app:app"'
EXPERIMENT_TARGET = '"worldshepherd_sara.persistent_audit_benchmark_app:app"'


source_path = Path(__file__).with_name("benchmark_fusion_real_network.py")
source = source_path.read_text(encoding="utf-8")
if source.count(SOURCE_TARGET) != 1:
    raise RuntimeError(
        "Expected exactly one default SARA Uvicorn target in real-network benchmark"
    )
source = source.replace(SOURCE_TARGET, EXPERIMENT_TARGET, 1)
exec(
    compile(source, str(source_path), "exec"),
    {"__name__": "__main__", "__file__": str(source_path)},
)
