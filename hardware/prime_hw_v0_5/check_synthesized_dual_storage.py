#!/usr/bin/env python3
"""Audit the Yosys evidence netlist for distinct primary/shadow state storage."""

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def parse_width(parameter) -> int | None:
    if parameter is None:
        return None
    if isinstance(parameter, int):
        return parameter
    if isinstance(parameter, str):
        text = parameter.strip()
        try:
            # Yosys JSON commonly serializes parameter integers as binary strings.
            if text and set(text) <= {"0", "1"}:
                return int(text, 2)
            return int(text, 0)
        except ValueError:
            return None
    return None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_synthesized_dual_storage.py <yosys-json>")

    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    modules = data.get("modules", {})
    top_name = "prime_hw_policy_controller_diverse"
    if top_name not in modules:
        fail(f"top module {top_name!r} missing from JSON")

    top = modules[top_name]
    netnames = top.get("netnames", {})

    required = {
        "primary_state_q": 8,
        "shadow_state_q": 7,
    }
    bitsets: dict[str, set[int]] = {}

    for name, width in required.items():
        if name not in netnames:
            fail(f"preserved state net {name!r} missing")
        bits = netnames[name].get("bits", [])
        if len(bits) != width:
            fail(f"{name} width is {len(bits)}, expected {width}")
        if any(not isinstance(bit, int) for bit in bits):
            fail(f"{name} contains constant/non-net bits: {bits}")
        if len(set(bits)) != width:
            fail(f"{name} aliases bits internally: {bits}")
        bitsets[name] = set(bits)

        attrs = netnames[name].get("attributes", {})
        if not any(str(key).lower() == "keep" for key in attrs):
            fail(f"{name} lacks preserved keep attribute in evidence netlist")

    overlap = bitsets["primary_state_q"] & bitsets["shadow_state_q"]
    if overlap:
        fail(f"primary and shadow state storage share synthesized net bits: {sorted(overlap)}")

    sequential_q_bits: set[int] = set()
    sequential_cells = []
    for cell_name, cell in top.get("cells", {}).items():
        cell_type = str(cell.get("type", ""))
        lower_type = cell_type.lower()
        if "dff" not in lower_type and "ff" not in lower_type:
            continue
        q_bits = cell.get("connections", {}).get("Q", [])
        q_net_bits = {bit for bit in q_bits if isinstance(bit, int)}
        if q_net_bits:
            sequential_q_bits |= q_net_bits
            sequential_cells.append((cell_name, cell_type, parse_width(cell.get("parameters", {}).get("WIDTH"))))

    all_state_bits = bitsets["primary_state_q"] | bitsets["shadow_state_q"]
    missing = all_state_bits - sequential_q_bits
    if missing:
        fail(f"state bits not driven by sequential cells: {sorted(missing)}")

    if len(all_state_bits) != 15:
        fail(f"expected 15 disjoint stored state bits, found {len(all_state_bits)}")

    print("PASS: synthesized evidence netlist preserves 8-bit primary and 7-bit shadow state nets")
    print("PASS: primary/shadow state nets are disjoint (15 unique stored state bits)")
    print(f"PASS: all 15 state bits are driven by sequential cells ({len(sequential_cells)} sequential cells observed)")
    if sequential_cells:
        print("INFO: sequential cells=" + ", ".join(
            f"{name}:{ctype}:width={width}" for name, ctype, width in sequential_cells
        ))


if __name__ == "__main__":
    main()
