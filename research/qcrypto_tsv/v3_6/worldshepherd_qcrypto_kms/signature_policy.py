"""Structural signature and sighash policy for PSBT signing boundaries.

This module validates encoding/range/sighash semantics. It does not verify a
signature against a transaction digest; that remains the signer's/Bitcoin Core's
cryptographic job.
"""
from __future__ import annotations

from dataclasses import dataclass


class SignaturePolicyError(RuntimeError):
    pass


SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
HALF_N = SECP256K1_N // 2

SIGHASH_DEFAULT = 0x00
SIGHASH_ALL = 0x01
SIGHASH_NONE = 0x02
SIGHASH_SINGLE = 0x03
SIGHASH_ANYONECANPAY = 0x80
_VALID_ECDSA_SIGHASHES = {1, 2, 3, 0x81, 0x82, 0x83}
_VALID_TAPROOT_SIGHASHES = {0, 1, 2, 3, 0x81, 0x82, 0x83}


@dataclass(frozen=True)
class ParsedEcdsaSignature:
    r: int
    s: int
    sighash_type: int
    low_s: bool


@dataclass(frozen=True)
class ParsedSchnorrSignature:
    r: int
    s: int
    sighash_type: int


def parse_strict_der_ecdsa_signature(sig_with_hashtype: bytes, *, require_low_s: bool = True) -> ParsedEcdsaSignature:
    sig = bytes(sig_with_hashtype)
    if len(sig) < 9 or len(sig) > 73:
        raise SignaturePolicyError("ECDSA signature including sighash must be 9..73 bytes")
    sighash = sig[-1]
    if sighash not in _VALID_ECDSA_SIGHASHES:
        raise SignaturePolicyError("invalid ECDSA sighash type")
    der = sig[:-1]
    if len(der) < 8 or der[0] != 0x30 or der[1] != len(der) - 2:
        raise SignaturePolicyError("ECDSA signature is not strict DER")
    if der[2] != 0x02:
        raise SignaturePolicyError("ECDSA R is not an INTEGER")
    len_r = der[3]
    if len_r == 0 or 4 + len_r + 2 > len(der):
        raise SignaturePolicyError("invalid ECDSA R length")
    r_bytes = der[4:4 + len_r]
    s_tag = 4 + len_r
    if der[s_tag] != 0x02:
        raise SignaturePolicyError("ECDSA S is not an INTEGER")
    len_s = der[s_tag + 1]
    s_bytes = der[s_tag + 2:s_tag + 2 + len_s]
    if len_s == 0 or s_tag + 2 + len_s != len(der):
        raise SignaturePolicyError("invalid ECDSA S length")
    for name, b in (("R", r_bytes), ("S", s_bytes)):
        if b[0] & 0x80:
            raise SignaturePolicyError(f"ECDSA {name} must be positive")
        if len(b) > 1 and b[0] == 0 and not (b[1] & 0x80):
            raise SignaturePolicyError(f"ECDSA {name} has redundant leading zero")
    r = int.from_bytes(r_bytes, "big")
    s = int.from_bytes(s_bytes, "big")
    if not 1 <= r < SECP256K1_N or not 1 <= s < SECP256K1_N:
        raise SignaturePolicyError("ECDSA scalar is outside secp256k1 range")
    low_s = s <= HALF_N
    if require_low_s and not low_s:
        raise SignaturePolicyError("ECDSA signature violates low-S policy")
    return ParsedEcdsaSignature(r=r, s=s, sighash_type=sighash, low_s=low_s)


def parse_schnorr_signature(signature: bytes) -> ParsedSchnorrSignature:
    sig = bytes(signature)
    if len(sig) not in (64, 65):
        raise SignaturePolicyError("Schnorr signature must be 64 or 65 bytes")
    r = int.from_bytes(sig[:32], "big")
    s = int.from_bytes(sig[32:64], "big")
    if r >= SECP256K1_P:
        raise SignaturePolicyError("Schnorr r is outside field range")
    if s >= SECP256K1_N:
        raise SignaturePolicyError("Schnorr s is outside scalar range")
    sighash = 0 if len(sig) == 64 else sig[64]
    if sighash not in _VALID_TAPROOT_SIGHASHES:
        raise SignaturePolicyError("invalid Taproot sighash type")
    if len(sig) == 65 and sighash == 0:
        raise SignaturePolicyError("explicit Taproot SIGHASH_DEFAULT byte is non-canonical")
    return ParsedSchnorrSignature(r=r, s=s, sighash_type=sighash)


def enforce_sighash_policy(
    sighash_type: int,
    *,
    taproot: bool,
    allow_none: bool = False,
    allow_single: bool = False,
    allow_anyonecanpay: bool = False,
) -> None:
    valid = _VALID_TAPROOT_SIGHASHES if taproot else _VALID_ECDSA_SIGHASHES
    if sighash_type not in valid:
        raise SignaturePolicyError("unknown sighash type")
    base = sighash_type & 0x03
    if sighash_type & SIGHASH_ANYONECANPAY and not allow_anyonecanpay:
        raise SignaturePolicyError("SIGHASH_ANYONECANPAY is blocked at this signing boundary")
    if base == SIGHASH_NONE and not allow_none:
        raise SignaturePolicyError("SIGHASH_NONE is blocked at this signing boundary")
    if base == SIGHASH_SINGLE and not allow_single:
        raise SignaturePolicyError("SIGHASH_SINGLE is blocked at this signing boundary")
    # base 0 is valid only for Taproot DEFAULT; ECDSA valid set excludes it.
