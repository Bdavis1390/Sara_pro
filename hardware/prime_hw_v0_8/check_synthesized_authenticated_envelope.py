#!/usr/bin/env python3
"""Audit Yosys JSON for PRIME-HW v0.8 authenticated command binding."""

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

TOP = "prime_hw_policy_controller_authenticated_hardened"
GUARD = "prime_hw_authenticated_envelope_guard"
TEMPORAL = "prime_hw_temporal_command_guard"
LATCH = "prime_hw_authentication_fault_latch"


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


def net_bits(module: dict, name: str, width: int = 1, require_keep: bool = False) -> set[int]:
    entry = module.get("netnames", {}).get(name)
    if entry is None:
        fail(f"net {name!r} missing")
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
        for out_bit in outs:
            drivers[out_bit] |= ins
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


def require_fanin(module: dict, output: str, inputs: tuple[str, ...]) -> None:
    drivers = build_driver_inputs(module)
    fanin = transitive_fanin(port_bits(module, output), drivers)
    for name in inputs:
        bits = port_bits(module, name)
        if not bits <= fanin:
            fail(f"{output} cone does not include complete {name} input")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_synthesized_authenticated_envelope.py <yosys-json>")

    data = json.loads(Path(sys.argv[1]).read_text())
    top = module_or_fail(data, TOP)
    guard = module_or_fail(data, GUARD)
    latch = module_or_fail(data, LATCH)

    # Exact authenticated admission must structurally depend on every declared
    # trust/binding input and the sticky authentication latch.
    require_fanin(
        guard,
        "authenticated_allow",
        (
            "policy_allow", "request_valid", "trusted_epoch_valid", "trusted_epoch",
            "verifier_valid", "verified_epoch", "verified_seq",
            "verified_command_digest", "command_epoch", "command_seq",
            "command_digest", "authentication_fault_latched",
        ),
    )
    require_fanin(
        guard,
        "authentication_integrity_fault",
        (
            "policy_allow", "request_valid", "trusted_epoch_valid", "trusted_epoch",
            "verifier_valid", "verified_epoch", "verified_seq",
            "verified_command_digest", "command_epoch", "command_seq", "command_digest",
        ),
    )
    require_fanin(
        guard,
        "envelope_binding_valid",
        (
            "trusted_epoch_valid", "trusted_epoch", "verifier_valid", "verified_epoch",
            "verified_seq", "verified_command_digest", "command_epoch", "command_seq",
            "command_digest",
        ),
    )

    # The dedicated authentication latch must still be sequential state.
    latch_q = port_bits(latch, "authentication_fault_latched")
    if not latch_q <= sequential_output_bits(latch):
        fail("authentication fault latch is not sequentially driven in evidence netlist")

    auth_allow_net = net_bits(top, "authenticated_allow_q", require_keep=True)
    auth_latch_net = net_bits(top, "authentication_fault_latched_q", require_keep=True)

    envelope_cell = find_unique_cell(top, GUARD)
    temporal_cell = find_unique_cell(top, TEMPORAL)
    latch_cell = find_unique_cell(top, LATCH)

    if conn_bits(envelope_cell, "policy_allow") != port_bits(top, "policy_allow"):
        fail("envelope guard is not fed by top policy_allow")
    if conn_bits(envelope_cell, "request_valid") != port_bits(top, "request_valid"):
        fail("envelope guard request_valid is not the top request rail")
    if conn_bits(envelope_cell, "authenticated_allow") != auth_allow_net:
        fail("envelope guard authenticated_allow does not drive preserved admission rail")
    if conn_bits(envelope_cell, "authentication_fault_latched") != auth_latch_net:
        fail("envelope guard does not consume preserved authentication latch rail")
    if conn_bits(envelope_cell, "authentication_integrity_fault") != port_bits(top, "authentication_integrity_fault"):
        fail("top authentication_integrity_fault is not the envelope guard output")
    if conn_bits(envelope_cell, "envelope_binding_valid") != port_bits(top, "envelope_binding_valid"):
        fail("top envelope_binding_valid is not the envelope guard output")

    if conn_bits(latch_cell, "authentication_integrity_fault") != port_bits(top, "authentication_integrity_fault"):
        fail("authentication latch is not driven by envelope integrity fault")
    if conn_bits(latch_cell, "authentication_fault_latched") != auth_latch_net:
        fail("authentication latch output does not drive preserved latch rail")

    if conn_bits(temporal_cell, "upstream_allow") != auth_allow_net:
        fail("v0.7 temporal gate is not fed by authenticated admission rail")
    if conn_bits(temporal_cell, "command_seq") != port_bits(top, "command_seq"):
        fail("temporal gate command sequence is not the live top command sequence")
    if conn_bits(temporal_cell, "execute_pulse") != port_bits(top, "execute_pulse"):
        fail("top execute_pulse is not the v0.7 temporal gate output")

    # Authentication and temporal sticky faults must both feed semantic SAFE
    # through the wrapper's effective fatal path.
    top_drivers = build_driver_inputs(top)
    safe_fanin = transitive_fanin(port_bits(top, "safe_state"), top_drivers)
    if not auth_latch_net <= safe_fanin:
        fail("SAFE-state cone lacks authentication-fault escalation path")
    if not port_bits(top, "temporal_fault_latched") <= safe_fanin:
        fail("SAFE-state cone lacks temporal-fault escalation path")

    print("PASS: authenticated admission cone contains every declared epoch/sequence/digest binding input and sticky authentication latch")
    print("PASS: authentication-integrity-fault and envelope-binding cones contain the complete declared live/verifier tuple")
    print("PASS: authentication fault capture remains sequential and feeds the SAFE-state escalation cone")
    print("PASS: v0.7 temporal gate consumes only the preserved authenticated admission rail and directly drives final execute_pulse")


if __name__ == "__main__":
    main()
