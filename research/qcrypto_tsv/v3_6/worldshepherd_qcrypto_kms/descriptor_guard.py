"""Output descriptor boundary validation for high-assurance Bitcoin signing.

Implements the BIP-380 descriptor checksum and a conservative exposure scanner.
This is not a complete Miniscript/descriptor semantic interpreter; Bitcoin Core
interop is still the authoritative semantic cross-check when available.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass


class DescriptorGuardError(RuntimeError):
    pass


INPUT_CHARSET = "0123456789()[],'/*abcdefgh@:$%{}IJKLMNOPQRSTUVWXYZ&+-.;<=>?!^_|~ijklmnopqrstuvwxyzABCDEFGH`#\"\\ "
CHECKSUM_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
GENERATOR = (0xF5DEE51989, 0xA9FDCA3312, 0x1BAB10E32D, 0x3706B1677A, 0x644D626FFD)

_EXT_PRIVATE_RE = re.compile(r"(?<![A-Za-z0-9])(?:xprv|tprv|yprv|zprv|Yprv|Zprv)[1-9A-HJ-NP-Za-km-z]{40,120}")
_EXT_PUBLIC_RE = re.compile(r"(?<![A-Za-z0-9])(?:xpub|tpub|ypub|zpub|Ypub|Zpub)[1-9A-HJ-NP-Za-km-z]{40,120}")
_RAW_PUBKEY_RE = re.compile(r"(?<![0-9A-Fa-f])(?:02|03)[0-9A-Fa-f]{64}(?![0-9A-Fa-f])|(?<![0-9A-Fa-f])04[0-9A-Fa-f]{128}(?![0-9A-Fa-f])")
_XONLY_RE = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])")
_BASE58_TOKEN_RE = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{50,52}(?![1-9A-HJ-NP-Za-km-z])")
_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


@dataclass(frozen=True)
class DescriptorAudit:
    descriptor_sha256: str
    allowed_for_external_signing_boundary: bool
    script_family: str
    checksum_present: bool
    checksum_valid: bool | None
    private_extended_key_count: int
    wif_private_key_count: int
    public_extended_key_count: int
    raw_public_key_count: int
    xonly_key_candidate_count: int
    findings: tuple[str, ...]
    required_controls: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _descsum_polymod(symbols: list[int]) -> int:
    chk = 1
    for value in symbols:
        top = chk >> 35
        chk = ((chk & 0x7FFFFFFFF) << 5) ^ value
        for i in range(5):
            if (top >> i) & 1:
                chk ^= GENERATOR[i]
    return chk


def _descsum_expand(text: str) -> list[int] | None:
    groups: list[int] = []
    symbols: list[int] = []
    for ch in text:
        pos = INPUT_CHARSET.find(ch)
        if pos < 0:
            return None
        symbols.append(pos & 31)
        groups.append(pos >> 5)
        if len(groups) == 3:
            symbols.append(groups[0] * 9 + groups[1] * 3 + groups[2])
            groups.clear()
    if len(groups) == 1:
        symbols.append(groups[0])
    elif len(groups) == 2:
        symbols.append(groups[0] * 3 + groups[1])
    return symbols


def descriptor_checksum(body: str) -> str:
    symbols = _descsum_expand(body)
    if symbols is None:
        raise DescriptorGuardError("descriptor contains a character outside the BIP-380 checksum character set")
    checksum = _descsum_polymod(symbols + [0] * 8) ^ 1
    return "".join(CHECKSUM_CHARSET[(checksum >> (5 * (7 - i))) & 31] for i in range(8))


def descriptor_with_checksum(body: str) -> str:
    if "#" in body:
        raise DescriptorGuardError("descriptor body passed for checksum creation must not contain '#'")
    return f"{body}#{descriptor_checksum(body)}"


def descriptor_checksum_valid(text: str) -> bool:
    if len(text) < 10 or text[-9] != "#":
        return False
    supplied = text[-8:]
    if any(ch not in CHECKSUM_CHARSET for ch in supplied):
        return False
    body = text[:-9]
    symbols = _descsum_expand(body)
    if symbols is None:
        return False
    return _descsum_polymod(symbols + [CHECKSUM_CHARSET.find(ch) for ch in supplied]) == 1


def _split_checksum(text: str) -> tuple[str, bool, bool | None]:
    hash_count = text.count("#")
    if hash_count == 0:
        return text, False, None
    if hash_count != 1 or len(text.rsplit("#", 1)[1]) != 8:
        return text.split("#", 1)[0], True, False
    body, _checksum = text.rsplit("#", 1)
    return body, True, descriptor_checksum_valid(text)


def _base58check_payload(token: str) -> bytes | None:
    value = 0
    try:
        for ch in token:
            value = value * 58 + _BASE58_ALPHABET.index(ch)
    except ValueError:
        return None
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big") if value else b""
    raw = b"\x00" * (len(token) - len(token.lstrip("1"))) + raw
    if len(raw) < 5:
        return None
    payload, checksum = raw[:-4], raw[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return payload if checksum == expected else None


def _find_wif_tokens(text: str) -> list[str]:
    out: list[str] = []
    for token in _BASE58_TOKEN_RE.findall(text):
        payload = _base58check_payload(token)
        if payload is None or payload[:1] not in {b"\x80", b"\xef"}:
            continue
        if len(payload) == 33 or (len(payload) == 34 and payload[-1:] == b"\x01"):
            out.append(token)
    return out


def _script_family(body: str) -> str:
    compact = "".join(body.split()).lower()
    if compact.startswith("tr("):
        return "P2TR"
    if compact.startswith("pk("):
        return "P2PK"
    if compact.startswith("combo("):
        return "COMBO_INCLUDES_P2PK"
    if compact.startswith("pkh("):
        return "P2PKH"
    if compact.startswith("wpkh(") or compact.startswith("sh(wpkh("):
        return "P2WPKH_FAMILY"
    if compact.startswith("wsh(") or compact.startswith("sh(wsh("):
        return "P2WSH_FAMILY"
    if compact.startswith("multi(") or compact.startswith("sortedmulti("):
        return "BARE_MULTISIG"
    if compact.startswith("addr("):
        return "ADDR_LITERAL"
    if compact.startswith("raw("):
        return "RAW_SCRIPT"
    return "UNKNOWN"


def audit_descriptor(
    descriptor: str,
    *,
    allow_public_extended_keys: bool = False,
    require_checksum: bool = False,
) -> DescriptorAudit:
    if not isinstance(descriptor, str) or not descriptor.strip():
        raise DescriptorGuardError("descriptor must be non-empty text")
    if len(descriptor) > 100_000:
        raise DescriptorGuardError("descriptor exceeds safety size")
    text = descriptor.strip()
    body, checksum_present, checksum_valid = _split_checksum(text)
    family = _script_family(body)
    private_keys = _EXT_PRIVATE_RE.findall(body)
    wif_keys = _find_wif_tokens(body)
    public_keys = _EXT_PUBLIC_RE.findall(body)
    raw_pubkeys = _RAW_PUBKEY_RE.findall(body)
    xonly_candidates = _XONLY_RE.findall(body)

    findings: list[str] = []
    controls: list[str] = []
    allowed = True

    if checksum_present and not checksum_valid:
        allowed = False
        findings.append("descriptor checksum is invalid")
        controls.append("REGENERATE_DESCRIPTOR_FROM_TRUSTED_SOURCE")
    elif checksum_present:
        findings.append("descriptor BIP-380 checksum verified")
    elif require_checksum:
        allowed = False
        findings.append("descriptor checksum is required at this signing boundary")
        controls.append("ADD_AND_VERIFY_BIP380_CHECKSUM")
    else:
        findings.append("descriptor has no checksum; permitted only because checksum policy is not mandatory")

    if private_keys or wif_keys:
        allowed = False
        if private_keys:
            findings.append("descriptor contains extended private-key material")
        if wif_keys:
            findings.append("descriptor contains WIF private-key material")
        controls.extend(("REMOVE_PRIVATE_KEYS_FROM_TRANSFER_DESCRIPTOR", "ROTATE_IF_EXPOSED_OUTSIDE_TRUST_BOUNDARY"))
    if public_keys:
        findings.append("descriptor contains extended public keys capable of unhardened public derivation")
        controls.append("MINIMIZE_XPUB_SCOPE_AND_DISTRIBUTION")
        if not allow_public_extended_keys:
            allowed = False
            controls.append("REJECT_XPUB_AT_EXTERNAL_SIGNING_BOUNDARY")

    if family in {"P2TR", "P2PK", "COMBO_INCLUDES_P2PK", "BARE_MULTISIG"}:
        findings.append(f"{family} can create long-lived public-key exposure under the current quantum-risk model")
        controls.append("DO_NOT_CREATE_NEW_LONG_EXPOSURE_OUTPUTS_IN_HARDENED_POLICY")
    elif family in {"P2PKH", "P2WPKH_FAMILY", "P2WSH_FAMILY"}:
        findings.append("hash-committed output family normally hides key/script material until spend, subject to reuse and spend-window risk")
        controls.extend(("NO_ADDRESS_REUSE", "PREPARE_SHORT_EXPOSURE_MITIGATION"))
    elif family in {"ADDR_LITERAL", "RAW_SCRIPT", "UNKNOWN"}:
        allowed = False
        findings.append("descriptor script semantics are not sufficiently classified by this guard")
        controls.append("FULL_DESCRIPTOR_SEMANTIC_VALIDATION_REQUIRED")

    if raw_pubkeys or (family == "P2TR" and xonly_candidates):
        findings.append("descriptor directly contains public-key material")

    return DescriptorAudit(
        descriptor_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        allowed_for_external_signing_boundary=allowed,
        script_family=family,
        checksum_present=checksum_present,
        checksum_valid=checksum_valid,
        private_extended_key_count=len(private_keys),
        wif_private_key_count=len(wif_keys),
        public_extended_key_count=len(public_keys),
        raw_public_key_count=len(raw_pubkeys),
        xonly_key_candidate_count=len(xonly_candidates),
        findings=tuple(findings),
        required_controls=tuple(dict.fromkeys(controls)),
    )
