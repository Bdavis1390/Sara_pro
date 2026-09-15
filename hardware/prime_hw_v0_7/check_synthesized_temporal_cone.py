#!/usr/bin/env python3
"""Audit Yosys JSON for PRIME-HW v0.7 temporal command integrity."""

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

TOP = "prime_hw_policy_controller_temporal_hardened"
GUARD = "prime_hw_temporal_command_guard"


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def module_or_fail(data: dict, name: str) -> dict:
    module = data.get("modules", {}).get(name)
    if module is None:
        fail(f"module {name!r} missing from synthesized JSON")
    return module


def port_bits(module: dict, name: str) -> set[int]:
    entry = module.get("ports", {}).get(name)
    if entry is None:
        fail(f"port {name!r} missing")
    bits = {b for b in entry.get("bits", []) if isinstance(b, int)}
    if not bits:
        fail(f"port {name!r} has no synthesized net bits")
    return bits


def net_bits(module: dict, name: str, width: int, require_keep: bool = False) -> set[int]:
    entry = module.get("netnames", {}).get(name)
    if entry is None:
        fail(f"preserved net {name!r} missing")
    bits = {b for b in entry.get("bits", []) if isinstance(b, int)}
    if len(bits) != width:
        fail(f"net {name!r} width is {len(bits)}, expected {width}")
    if require_keep:
        attrs = entry.get("attributes", {})
        if not any(str(k).lower() == "keep" for k in attrs):
            fail(f"net {name!r} lacks keep attribute")
    return bits


def build_driver_inputs(module: dict) -> dict[int, set[int]]:
    drivers: dict[int, set[int]] = defaultdict(set)
    for cell in module.get("cells", {}).values():
        directions = cell.get("port_directions", {})
        connections = cell.get("connections", {})
        ins: set[int] = set()
        outs: set[int] = set()
        for port_name, direction in directions.items():
            bits = {b for b in connections.get(port_name, []) if isinstance(b, int)}
            if direction in ("input", "inout"):
                ins |= bits
            if direction in ("output", "inout"):
                outs |= bits
        for bit in outs:
            drivers[bit] |= ins
    return drivers


def transitive_fanin(start_bits: set[int], drivers: dict[int, set[int]]) -> set[int]:
    seen = set(start_bits)
    queue = deque(start_bits)
    while queue:
        bit = queue.popleft()
        for parent in drivers.get(bit, ()):
            if parent not in seen:
                seen.add(parent)
                queue.append(parent)
    return seen


def sequential_output_bits(module: dict) -> set[int]:
    outputs: set[int] = set()
    for cell in module.get("cells", {}).values():
        ctype = str(cell.get("type", "")).lower()
        if "dff" not in ctype:
            continue
        directions = cell.get("port_directions", {})
        connections = cell.get("connections", {})
        for port_name, direction in directions.items():
            if direction == "output" and port_name.upper().startswith("Q"):
                outputs |= {b for b in connections.get(port_name, []) if isinstance(b, int)}
    return outputs


def find_unique_cell(module: dict, ctype: str) -> dict:
    matches = [cell for cell in module.get("cells", {}).values() if cell.get("type") == ctype]
    if len(matches) != 1:
        fail(f"expected exactly one {ctype!r} cell, found {len(matches)}")
    return matches[0]


def conn_bits(cell: dict, port: str) -> set[int]:
    return {b for b in cell.get("connections", {}).get(port, []) if isinstance(b, int)}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_synthesized_temporal_cone.py <yosys-json>")

    data = json.loads(Path(sys.argv[1]).read_text())
    top = module_or_fail(data, TOP)
    guard = module_or_fail(data, GUARD)

    primary = net_bits(guard, "expected_seq_q", 8, require_keep=True)
    inverse = net_bits(guard, "expected_seq_inv_q", 8, require_keep=True)
    latched = net_bits(guard, "temporal_fault_latched_q", 1, require_keep=True)

    if primary & inverse:
        fail("primary and inverse sequence stores alias in synthesized guard")
    if len(primary | inverse) != 16:
        fail("sequence stores do not preserve 16 disjoint logical state bits")

    seq_outputs = sequential_output_bits(guard)
    required_state = primary | inverse | latched
    if not required_state <= seq_outputs:
        missing = sorted(required_state - seq_outputs)
        fail(f"preserved temporal state bits are not all sequentially driven: {missing}")

    drivers = build_driver_inputs(guard)
    execute_fanin = transitive_fanin(port_bits(guard, "execute_pulse"), drivers)
    fault_fanin = transitive_fanin(port_bits(guard, "temporal_integrity_fault"), drivers)

    execute_requirements = {
        "primary sequence state": primary,
        "inverse sequence state": inverse,
        "sticky temporal fault latch": latched,
        "upstream allow": port_bits(guard, "upstream_allow"),
        "request valid": port_bits(guard, "request_valid"),
        "command sequence": port_bits(guard, "command_seq"),
    }
    for label, bits in execute_requirements.items():
        if not bits <= execute_fanin:
            fail(f"execute cone does not include {label}")

    for label, bits in {
        "primary sequence state": primary,
        "inverse sequence state": inverse,
        "upstream allow": port_bits(guard, "upstream_allow"),
        "request valid": port_bits(guard, "request_valid"),
        "command sequence": port_bits(guard, "command_seq"),
    }.items():
        if not bits <= fault_fanin:
            fail(f"temporal-integrity-fault cone does not include {label}")

    # Verify top-level integration rather than auditing the guard in isolation.
    guard_cell = find_unique_cell(top, GUARD)
    if conn_bits(guard_cell, "execute_pulse") != port_bits(top, "execute_pulse"):
        fail("top execute_pulse is not directly driven by the temporal guard")
    if conn_bits(guard_cell, "upstream_allow") != port_bits(top, "policy_allow"):
        fail("temporal guard upstream_allow is not the top policy_allow rail")
    if conn_bits(guard_cell, "request_valid") != port_bits(top, "request_valid"):
        fail("temporal guard request_valid is not the top request_valid rail")
    if conn_bits(guard_cell, "command_seq") != port_bits(top, "command_seq"):
        fail("temporal guard command_seq is not the top command_seq bus")
    if conn_bits(guard_cell, "temporal_fault_latched") != port_bits(top, "temporal_fault_latched"):
        fail("top temporal fault latch output is not the guard latch rail")

    top_drivers = build_driver_inputs(top)
    safe_fanin = transitive_fanin(port_bits(top, "safe_state"), top_drivers)
    if not port_bits(top, "temporal_fault_latched") <= safe_fanin:
        fail("SAFE-state cone lacks temporal-fault escalation path")

    print("PASS: synthesized temporal guard preserves 8+8 disjoint sequence-state bits plus sticky latch as sequential state")
    print("PASS: execute cone contains both sequence representations, sticky latch, upstream allow, request-valid, and command sequence")
    print("PASS: temporal-fault cone contains both sequence representations and the transaction identity inputs")
    print("PASS: top-level execute rail is the temporal guard output and temporal latch has a SAFE-state escalation path")


if __name__ == "__main__":
    main()
