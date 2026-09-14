#!/usr/bin/env python3
"""Exhaustively audit the PRIME-HW v0.5 dual-representation state guard."""

PRIMARY = {
    "RESET": 0x00,
    "BOOT_LOCKED": 0x0F,
    "VERIFY": 0x33,
    "OPERATIONAL": 0x3C,
    "DEGRADED": 0x55,
    "SAFE": 0x5A,
    "RECOVERY": 0x66,
}

SHADOW = {
    "RESET": 0b0000001,
    "BOOT_LOCKED": 0b0000010,
    "VERIFY": 0b0000100,
    "OPERATIONAL": 0b0001000,
    "DEGRADED": 0b0010000,
    "SAFE": 0b0100000,
    "RECOVERY": 0b1000000,
}

PRIMARY_DECODE = {value: name for name, value in PRIMARY.items()}
SHADOW_DECODE = {value: name for name, value in SHADOW.items()}


def integrity_fault(primary: int, shadow: int) -> bool:
    p = PRIMARY_DECODE.get(primary)
    s = SHADOW_DECODE.get(shadow)
    return p is None or s is None or p != s


def main() -> None:
    accepted = []
    for primary in range(256):
        for shadow in range(128):
            if not integrity_fault(primary, shadow):
                accepted.append((primary, shadow))

    expected = {(PRIMARY[name], SHADOW[name]) for name in PRIMARY}
    if set(accepted) != expected:
        raise SystemExit(
            "FAIL: dual guard acceptance set differs from the seven exact matched state pairs"
        )

    primary_mutations = 0
    shadow_mutations = 0
    for name in PRIMARY:
        base_primary = PRIMARY[name]
        base_shadow = SHADOW[name]

        for mask in range(1, 256):
            primary_mutations += 1
            if not integrity_fault(base_primary ^ mask, base_shadow):
                raise SystemExit(
                    f"FAIL: primary mutation escaped detection: {name} mask=0x{mask:02X}"
                )

        for mask in range(1, 128):
            shadow_mutations += 1
            if not integrity_fault(base_primary, base_shadow ^ mask):
                raise SystemExit(
                    f"FAIL: shadow mutation escaped detection: {name} mask=0x{mask:02X}"
                )

    total_mutations = primary_mutations + shadow_mutations
    print(
        "PASS: dual-state guard accepts exactly 7 matched pairs and faults "
        f"{32768 - len(accepted)} of 32768 encoded pairs"
    )
    print(
        "PASS: every nonzero arbitrary bit-mask mutation isolated to either state domain "
        f"is detected ({primary_mutations} primary + {shadow_mutations} shadow = {total_mutations} cases)"
    )


if __name__ == "__main__":
    main()
