#!/usr/bin/env python3
"""Audit Yosys JSON for the v0.6 fail-closed authorization cone."""

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

TOP = "prime_hw_policy_controller_authorization_hardened"
VOTE_NETS = (
    "core_allow_vote",
    "witness_allow_vote",
    "core_deny_vote",
    "witness_deny_vote",
)


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def net_bits(module: dict, name: str) -> set[int]:
    entry = module.get("netnames", {}).get(name)
    if entry is None:
        fail(f"preserved net {name!r} missing from synthesized JSON")
    bits = entry.get("bits", [])
    if len(bits) != 1 or not isinstance(bits[0], int):
        fail(f"preserved net {name!r} is not one synthesized scalar net bit: {bits}")
    attrs = entry.get("attributes", {})
    if not any(str(k).lower() == "keep" for k in attrs):
        fail(f"preserved net {name!r} lacks keep attribute")
    return {bits[0]}


def port_bits(module: dict, name: str) -> set[int]:
    entry = module.get("ports", {}).get(name)
    if entry is None:
        fail(f"top-level port {name!r} missing")
    bits = {b for b in entry.get("bits", []) if isinstance(b, int)}
    if not bits:
        fail(f"top-level port {name!r} has no net bits")
    return bits


def build_driver_inputs(module: dict) -> dict[int, set[int]]:
    drivers: dict[int, set[int]] = defaultdict(set)
    for cell in module.get("cells", {}).values():
        directions = cell.get("port_directions", {})
        connections = cell.get("connections", {})
        input_bits: set[int] = set()
        output_bits: set[int] = set()

        for port_name, direction in directions.items():
            bits = {b for b in connections.get(port_name, []) if isinstance(b, int)}
            if direction == "input":
                input_bits |= bits
            elif direction == "output":
                output_bits |= bits
            elif direction == "inout":
                input_bits |= bits
                output_bits |= bits

        for out_bit in output_bits:
            drivers[out_bit] |= input_bits
    return drivers


def transitive_fanin(start_bits: set[int], driver_inputs: dict[int, set[int]]) -> set[int]:
    seen = set(start_bits)
    queue = deque(start_bits)
    while queue:
        bit = queue.popleft()
        for parent in driver_inputs.get(bit, ()):
            if parent not in seen:
                seen.add(parent)
                queue.append(parent)
    return seen


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_synthesized_authorization_cone.py <yosys-json>")

    data = json.loads(Path(sys.argv[1]).read_text())
    module = data.get("modules", {}).get(TOP)
    if module is None:
        fail(f"top module {TOP!r} missing")

    vote_bits = {name: net_bits(module, name) for name in VOTE_NETS}
    all_vote_bits = set().union(*vote_bits.values())
    if len(all_vote_bits) != 4:
        fail("preserved vote rails alias each other in synthesized netlist")

    latched_bits = net_bits(module, "authorization_fault_latched_q")
    drivers = build_driver_inputs(module)

    allow_fanin = transitive_fanin(port_bits(module, "allow"), drivers)
    integrity_fanin = transitive_fanin(port_bits(module, "authorization_integrity_fault"), drivers)
    deny_fanin = transitive_fanin(port_bits(module, "deny"), drivers)

    for required in ("core_allow_vote", "witness_allow_vote"):
        if not (vote_bits[required] <= allow_fanin):
            fail(f"final allow cone does not include preserved {required}")

    if not (latched_bits <= allow_fanin):
        fail("final allow cone does not include sticky authorization-fault latch")

    for required in VOTE_NETS:
        if not (vote_bits[required] <= integrity_fanin):
            fail(f"authorization-integrity-fault cone does not include {required}")

    for required in ("core_allow_vote", "witness_allow_vote"):
        if not (vote_bits[required] <= deny_fanin):
            fail(f"final deny cone does not depend on voted allow path via {required}")

    print("PASS: four preserved authorization vote rails are distinct in the synthesized evidence netlist")
    print("PASS: final allow fan-in contains both independent allow-vote rails and the sticky fault latch")
    print("PASS: authorization-integrity-fault fan-in contains all four preserved allow/deny vote rails")
    print("PASS: final deny fan-in depends on the voted allow cone")


if __name__ == "__main__":
    main()
