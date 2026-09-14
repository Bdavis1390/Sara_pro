#!/usr/bin/env python3
"""Exhaustively verify the PRIME-HW v0.4 state-code fault-detection bound."""

from itertools import combinations

CODES = {
    "RESET": 0x00,
    "BOOT_LOCKED": 0x0F,
    "VERIFY": 0x33,
    "OPERATIONAL": 0x3C,
    "DEGRADED": 0x55,
    "SAFE": 0x5A,
    "RECOVERY": 0x66,
}


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def main() -> None:
    values = set(CODES.values())
    if len(values) != len(CODES):
        raise SystemExit("FAIL: state codewords are not unique")

    pair_distances = {
        (a_name, b_name): hamming_distance(a, b)
        for (a_name, a), (b_name, b) in combinations(CODES.items(), 2)
    }
    min_distance = min(pair_distances.values())
    if min_distance < 4:
        raise SystemExit(f"FAIL: minimum state-code distance is {min_distance}, expected >= 4")

    corruption_cases = 0
    for name, code in CODES.items():
        for width in (1, 2, 3):
            for bit_positions in combinations(range(8), width):
                mask = sum(1 << bit for bit in bit_positions)
                corrupted = code ^ mask
                corruption_cases += 1
                if corrupted in values:
                    raise SystemExit(
                        "FAIL: <=3-bit corruption aliases a valid codeword: "
                        f"{name}=0x{code:02X}, mask=0x{mask:02X}, result=0x{corrupted:02X}"
                    )

    print(f"PASS: {len(CODES)} unique codewords; minimum Hamming distance={min_distance}")
    print(
        "PASS: every 1-, 2-, and 3-bit corruption of every valid codeword "
        f"is non-aliasing ({corruption_cases} cases)"
    )


if __name__ == "__main__":
    main()
