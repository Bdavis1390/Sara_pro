"""Conservative BIP-360 P2MR v0.12.1 draft construction helpers.

This is experimental/reference code only. BIP-360 is Draft and SegWit v2 P2MR is
not activated Bitcoin consensus. The high-level address helper refuses mainnet, and
the high-level Merkle-root builder refuses depth-zero/single-leaf trees by default
because the current BIP draft specifies m=0 as anyone-can-spend.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Iterable, Sequence

BIP360_VERSION = "0.12.1"
P2MR_WITNESS_VERSION = 2
DEFAULT_LEAF_VERSION = 0xC0
_BECH32M_CONST = 0x2BC830A3
_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


class P2MrDraftError(RuntimeError):
    pass


def compact_size(n: int) -> bytes:
    if n < 0:
        raise P2MrDraftError("compact size cannot encode a negative integer")
    if n < 253:
        return bytes([n])
    if n <= 0xFFFF:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xFFFFFFFF:
        return b"\xfe" + n.to_bytes(4, "little")
    if n <= 0xFFFFFFFFFFFFFFFF:
        return b"\xff" + n.to_bytes(8, "little")
    raise P2MrDraftError("integer is too large for Bitcoin CompactSize")


def tagged_hash(tag: str, payload: bytes) -> bytes:
    tag_hash = hashlib.sha256(tag.encode("ascii")).digest()
    return hashlib.sha256(tag_hash + tag_hash + payload).digest()


def tapleaf_hash(script: bytes, leaf_version: int = DEFAULT_LEAF_VERSION) -> bytes:
    if not isinstance(script, (bytes, bytearray)):
        raise P2MrDraftError("script must be bytes")
    if not 0 <= leaf_version <= 255 or leaf_version & 1:
        raise P2MrDraftError("leaf version must be an even byte")
    script = bytes(script)
    return tagged_hash("TapLeaf", bytes([leaf_version]) + compact_size(len(script)) + script)


def tapbranch_hash(left: bytes, right: bytes) -> bytes:
    if len(left) != 32 or len(right) != 32:
        raise P2MrDraftError("TapBranch children must be 32-byte hashes")
    a, b = sorted((bytes(left), bytes(right)))
    return tagged_hash("TapBranch", a + b)


@dataclass(frozen=True)
class P2MrLeaf:
    script: bytes
    leaf_version: int = DEFAULT_LEAF_VERSION

    @property
    def hash(self) -> bytes:
        return tapleaf_hash(self.script, self.leaf_version)


def build_balanced_merkle_root(leaves: Sequence[P2MrLeaf], *, allow_single_leaf_test_vector: bool = False) -> bytes:
    """Build a deterministic balanced tree for local experiments.

    Bitcoin script trees are semantic trees, not unordered bags; production wallet
    code should preserve the intended tree topology. This helper is intentionally
    limited to a deterministic balanced construction for experiments.
    """
    if not leaves:
        raise P2MrDraftError("P2MR requires a script tree with at least one leaf")
    if len(leaves) == 1 and not allow_single_leaf_test_vector:
        raise P2MrDraftError("single-leaf/depth-zero P2MR is anyone-can-spend in the current draft")
    level = [leaf.hash for leaf in leaves]
    while len(level) > 1:
        next_level: list[bytes] = []
        for i in range(0, len(level), 2):
            if i + 1 == len(level):
                # Do not duplicate a leaf; carry the subtree upward unchanged.
                next_level.append(level[i])
            else:
                next_level.append(tapbranch_hash(level[i], level[i + 1]))
        level = next_level
    return level[0]


def p2mr_control_block(leaf_version: int, merkle_path: Sequence[bytes], *, allow_depth_zero_test_vector: bool = False) -> bytes:
    """Construct the current BIP-360 draft control block.

    P2MR omits the 32-byte Taproot internal key. The control byte retains the
    tapscript leaf-version encoding and its low bit is required to be 1. A
    depth-zero control block is refused by default because the current BIP draft
    makes m=0 anyone-can-spend.
    """
    if not 0 <= leaf_version <= 255 or leaf_version & 1:
        raise P2MrDraftError("leaf version must be an even byte")
    if len(merkle_path) > 128:
        raise P2MrDraftError("P2MR Merkle path depth exceeds 128")
    if len(merkle_path) == 0 and not allow_depth_zero_test_vector:
        raise P2MrDraftError("depth-zero P2MR control block is anyone-can-spend in the current draft")
    normalized: list[bytes] = []
    for node in merkle_path:
        if not isinstance(node, (bytes, bytearray)) or len(node) != 32:
            raise P2MrDraftError("every P2MR Merkle-path element must be 32 bytes")
        normalized.append(bytes(node))
    return bytes([leaf_version | 0x01]) + b"".join(normalized)


def verify_p2mr_merkle_path(
    *,
    script: bytes,
    control_block: bytes,
    expected_root: bytes,
    allow_depth_zero_test_vector: bool = False,
) -> bool:
    """Verify the P2MR script/control-block commitment against a witness root.

    This validates only the Merkle commitment mechanics. It does not execute
    tapscript, validate a Bitcoin transaction, or establish consensus activation.
    """
    if not isinstance(control_block, (bytes, bytearray)):
        raise P2MrDraftError("control block must be bytes")
    control_block = bytes(control_block)
    if len(control_block) < 1 or (len(control_block) - 1) % 32 != 0:
        raise P2MrDraftError("P2MR control block length must be 1 + 32*m bytes")
    depth = (len(control_block) - 1) // 32
    if depth > 128:
        raise P2MrDraftError("P2MR control block depth exceeds 128")
    if depth == 0 and not allow_depth_zero_test_vector:
        raise P2MrDraftError("depth-zero P2MR is refused because the current draft treats it as anyone-can-spend")
    if control_block[0] & 1 != 1:
        raise P2MrDraftError("P2MR control-byte low bit must be 1")
    if not isinstance(expected_root, (bytes, bytearray)) or len(expected_root) != 32:
        raise P2MrDraftError("expected P2MR root must be 32 bytes")
    leaf_version = control_block[0] & 0xFE
    current = tapleaf_hash(script, leaf_version)
    for offset in range(1, len(control_block), 32):
        current = tapbranch_hash(current, control_block[offset:offset + 32])
    return hmac.compare_digest(current, bytes(expected_root))


def p2mr_script_pubkey(merkle_root: bytes) -> bytes:
    if not isinstance(merkle_root, (bytes, bytearray)) or len(merkle_root) != 32:
        raise P2MrDraftError("P2MR Merkle root must be exactly 32 bytes")
    # OP_2 (0x52), OP_PUSHBYTES_32 (0x20), 32-byte witness program.
    return b"\x52\x20" + bytes(merkle_root)


def _bech32_polymod(values: Iterable[int]) -> int:
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


def _create_bech32m_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0] * 6) ^ _BECH32M_CONST
    return [(polymod >> (5 * (5 - i))) & 31 for i in range(6)]


def _convertbits(data: bytes, frombits: int, tobits: int, pad: bool = True) -> list[int]:
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or value >> frombits:
            raise P2MrDraftError("invalid data for bit conversion")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise P2MrDraftError("invalid non-zero bit conversion padding")
    return ret


def encode_segwit_v2_bech32m(hrp: str, witness_program: bytes) -> str:
    """Low-level BIP-350 encoder used for vector verification.

    This accepts `bc` so published BIP-360 vectors can be reproduced. Application
    code should use `experimental_p2mr_address`, which refuses mainnet.
    """
    if not hrp or hrp.lower() != hrp:
        raise P2MrDraftError("HRP must be non-empty lowercase text")
    if len(witness_program) != 32:
        raise P2MrDraftError("P2MR witness program must be 32 bytes")
    data = [P2MR_WITNESS_VERSION] + _convertbits(bytes(witness_program), 8, 5, True)
    checksum = _create_bech32m_checksum(hrp, data)
    return hrp + "1" + "".join(_CHARSET[d] for d in data + checksum)


def experimental_p2mr_address(merkle_root: bytes, *, network: str) -> str:
    network = network.strip().upper()
    if network in {"MAINNET", "BITCOIN_MAINNET", "BTC_MAINNET"}:
        raise P2MrDraftError("mainnet P2MR address generation is disabled while BIP-360 remains Draft/unactivated")
    hrp = {
        "SIGNET": "tb",
        "TESTNET4": "tb",
        "REGTEST": "bcrt",
    }.get(network)
    if hrp is None:
        raise P2MrDraftError("only SIGNET, TESTNET4 and REGTEST are allowed for experimental P2MR")
    return encode_segwit_v2_bech32m(hrp, bytes(merkle_root))
