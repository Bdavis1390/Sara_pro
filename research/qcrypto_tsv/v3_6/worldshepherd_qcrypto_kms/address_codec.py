"""Network-bound Bitcoin address/script conversion for signing-boundary checks.

Supports Base58Check P2PKH/P2SH and SegWit v0-v16 Bech32/Bech32m.  This module
only converts addresses to scriptPubKeys and back; it does not query a wallet or
assert ownership.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


class AddressCodecError(RuntimeError):
    pass


_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_CHARSET_REV = {c: i for i, c in enumerate(_CHARSET)}
_BECH32_CONST = 1
_BECH32M_CONST = 0x2BC830A3
_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _network_params(network: str) -> tuple[str, int, int]:
    n = network.strip().upper()
    if n in {"MAINNET", "BITCOIN_MAINNET", "BTC_MAINNET"}:
        return "bc", 0x00, 0x05
    if n in {"TESTNET", "TESTNET3", "TESTNET4", "SIGNET"}:
        return "tb", 0x6F, 0xC4
    if n == "REGTEST":
        return "bcrt", 0x6F, 0xC4
    raise AddressCodecError("unsupported Bitcoin network")


def _polymod(values: list[int]) -> int:
    generators = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ value
        for i, generator in enumerate(generators):
            if (top >> i) & 1:
                chk ^= generator
    return chk


def _hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def _convertbits(values, frombits: int, tobits: int, pad: bool) -> list[int]:
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in values:
        if value < 0 or value >> frombits:
            raise AddressCodecError("invalid value for bit conversion")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise AddressCodecError("invalid Bech32 padding")
    return ret


def _bech32_decode(address: str) -> tuple[str, list[int], int]:
    if not isinstance(address, str) or not (8 <= len(address) <= 90):
        raise AddressCodecError("invalid Bech32 address length")
    if address.lower() != address and address.upper() != address:
        raise AddressCodecError("mixed-case Bech32 address")
    a = address.lower()
    pos = a.rfind("1")
    if pos < 1 or pos + 7 > len(a):
        raise AddressCodecError("invalid Bech32 separator position")
    hrp = a[:pos]
    try:
        values = [_CHARSET_REV[c] for c in a[pos + 1:]]
    except KeyError as exc:
        raise AddressCodecError("invalid Bech32 character") from exc
    pm = _polymod(_hrp_expand(hrp) + values)
    if pm == _BECH32_CONST:
        enc = _BECH32_CONST
    elif pm == _BECH32M_CONST:
        enc = _BECH32M_CONST
    else:
        raise AddressCodecError("invalid Bech32 checksum")
    return hrp, values[:-6], enc


def _bech32_encode(hrp: str, data: list[int], const: int) -> str:
    pm = _polymod(_hrp_expand(hrp) + data + [0] * 6) ^ const
    checksum = [(pm >> (5 * (5 - i))) & 31 for i in range(6)]
    return hrp + "1" + "".join(_CHARSET[d] for d in data + checksum)


def _b58decode_check(address: str) -> bytes:
    if not isinstance(address, str) or not address:
        raise AddressCodecError("empty Base58 address")
    value = 0
    try:
        for ch in address:
            value = value * 58 + _BASE58.index(ch)
    except ValueError as exc:
        raise AddressCodecError("invalid Base58 character") from exc
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big") if value else b""
    raw = b"\x00" * (len(address) - len(address.lstrip("1"))) + raw
    if len(raw) < 5:
        raise AddressCodecError("Base58Check payload is too short")
    payload, checksum = raw[:-4], raw[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected:
        raise AddressCodecError("invalid Base58Check checksum")
    return payload


def _b58encode_check(payload: bytes) -> str:
    raw = payload + hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    value = int.from_bytes(raw, "big")
    chars: list[str] = []
    while value:
        value, rem = divmod(value, 58)
        chars.append(_BASE58[rem])
    leading = len(raw) - len(raw.lstrip(b"\x00"))
    return "1" * leading + ("".join(reversed(chars)) or "")


def address_to_scriptpubkey(address: str, *, network: str) -> bytes:
    """Decode an address and require that its network matches ``network``."""
    hrp, p2pkh_prefix, p2sh_prefix = _network_params(network)
    # SegWit addresses always contain a separator and are case-insensitive as a whole.
    if "1" in address and address.lower().split("1", 1)[0] in {"bc", "tb", "bcrt"}:
        got_hrp, data, encoding = _bech32_decode(address)
        if got_hrp != hrp:
            raise AddressCodecError("address HRP does not match requested network")
        if not data:
            raise AddressCodecError("SegWit address has no witness version")
        version = data[0]
        if not 0 <= version <= 16:
            raise AddressCodecError("invalid witness version")
        program = bytes(_convertbits(data[1:], 5, 8, False))
        if not 2 <= len(program) <= 40:
            raise AddressCodecError("invalid witness program length")
        if version == 0:
            if encoding != _BECH32_CONST or len(program) not in (20, 32):
                raise AddressCodecError("SegWit v0 requires Bech32 and a 20/32-byte program")
            opcode = 0x00
        else:
            if encoding != _BECH32M_CONST:
                raise AddressCodecError("SegWit v1+ requires Bech32m")
            opcode = 0x50 + version
        return bytes([opcode, len(program)]) + program

    payload = _b58decode_check(address)
    if len(payload) != 21:
        raise AddressCodecError("unsupported Base58Check address payload")
    prefix, h160 = payload[0], payload[1:]
    if prefix == p2pkh_prefix:
        return b"\x76\xa9\x14" + h160 + b"\x88\xac"
    if prefix == p2sh_prefix:
        return b"\xa9\x14" + h160 + b"\x87"
    raise AddressCodecError("Base58 address prefix does not match requested network")


def scriptpubkey_to_address(script: bytes, *, network: str) -> str:
    hrp, p2pkh_prefix, p2sh_prefix = _network_params(network)
    s = bytes(script)
    if len(s) == 25 and s[:3] == b"\x76\xa9\x14" and s[-2:] == b"\x88\xac":
        return _b58encode_check(bytes([p2pkh_prefix]) + s[3:23])
    if len(s) == 23 and s[:2] == b"\xa9\x14" and s[-1:] == b"\x87":
        return _b58encode_check(bytes([p2sh_prefix]) + s[2:22])
    if len(s) >= 4 and 2 <= s[1] <= 40 and len(s) == 2 + s[1]:
        if s[0] == 0:
            version = 0
        elif 0x51 <= s[0] <= 0x60:
            version = s[0] - 0x50
        else:
            raise AddressCodecError("script is not a supported address-bearing output")
        program = s[2:]
        if version == 0 and len(program) not in (20, 32):
            raise AddressCodecError("invalid SegWit v0 program length")
        const = _BECH32_CONST if version == 0 else _BECH32M_CONST
        data = [version] + _convertbits(program, 8, 5, True)
        return _bech32_encode(hrp, data, const)
    raise AddressCodecError("script is not a supported address-bearing output")


@dataclass(frozen=True)
class AddressBinding:
    address: str
    network: str
    script_pubkey_hex: str


def bind_address(address: str, *, network: str) -> AddressBinding:
    script = address_to_scriptpubkey(address, network=network)
    return AddressBinding(address=address, network=network.strip().upper(), script_pubkey_hex=script.hex())
