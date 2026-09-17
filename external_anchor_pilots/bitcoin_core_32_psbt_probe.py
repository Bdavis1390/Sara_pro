#!/usr/bin/env python3
"""BC32-001: Bitcoin Core 32 PSBT v2 compatibility probe.

Runs only against an isolated regtest node. It verifies that the four v32 PSBT
creation pathways covered by upstream rpc_psbt.py default to PSBT v2 and still
permit an explicit PSBT v0 request.

No mainnet/testnet connection is used and no real funds are involved. A technical
PASS is raw evidence only; this probe never self-promotes a Worldshepherd claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PINNED_UPSTREAM_TAG = "v32.0rc1"
PINNED_UPSTREAM_COMMIT = "d0231bb01d83178224bf7b198ba04f78cc2c89ef"
EXPECTED_VERSION_SUBSTRING = PINNED_UPSTREAM_TAG
CASE_CLAIM_CLASS = "NOT CURRENTLY CLAIMED"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def json_arg(value: Any) -> str:
    if isinstance(value, (dict, list, bool)) or value is None:
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def parse_cli_output(text: str) -> Any:
    """Parse bitcoin-cli output while preserving unquoted scalar strings."""
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


class CoreHarness:
    def __init__(self, bitcoind: str, bitcoin_cli: str, datadir: Path):
        self.bitcoind = bitcoind
        self.bitcoin_cli = bitcoin_cli
        self.datadir = datadir
        self.proc: subprocess.Popen[str] | None = None

    def cli(self, method: str, *args: Any, wallet: str | None = None) -> Any:
        cmd = [self.bitcoin_cli, f"-datadir={self.datadir}", "-regtest"]
        if wallet:
            cmd.append(f"-rpcwallet={wallet}")
        cmd.append(method)
        cmd.extend(json_arg(arg) for arg in args)
        return parse_cli_output(run(cmd).stdout)

    def named(self, method: str, params: dict[str, Any], *, wallet: str | None = None) -> Any:
        cmd = [self.bitcoin_cli, f"-datadir={self.datadir}", "-regtest"]
        if wallet:
            cmd.append(f"-rpcwallet={wallet}")
        cmd.extend(["-named", method])
        for key, value in params.items():
            cmd.append(f"{key}={json_arg(value)}")
        return parse_cli_output(run(cmd).stdout)

    def start(self) -> None:
        self.datadir.mkdir(parents=True, exist_ok=True)
        (self.datadir / "bitcoin.conf").write_text(
            "\n".join(
                [
                    "regtest=1",
                    "server=1",
                    "networkactive=0",
                    "listen=0",
                    "discover=0",
                    "dnsseed=0",
                    "fixedseeds=0",
                    "fallbackfee=0.0002",
                    "printtoconsole=0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.proc = subprocess.Popen(
            [self.bitcoind, f"-datadir={self.datadir}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        deadline = time.monotonic() + 30
        last_error = "RPC not ready"
        while time.monotonic() < deadline:
            try:
                info = self.cli("getblockchaininfo")
                if info["chain"] != "regtest":
                    raise RuntimeError(f"refusing non-regtest chain: {info['chain']}")
                return
            except (subprocess.CalledProcessError, KeyError, TypeError, RuntimeError) as exc:
                last_error = str(exc)
                if self.proc.poll() is not None:
                    raise RuntimeError(f"bitcoind exited early with code {self.proc.returncode}") from exc
                time.sleep(0.25)
        raise TimeoutError(f"bitcoind did not become RPC-ready within 30 seconds: {last_error}")

    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            self.cli("stop")
        except Exception:
            self.proc.terminate()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


def decode_version(harness: CoreHarness, psbt: str) -> int:
    decoded = harness.cli("decodepsbt", psbt)
    return int(decoded["psbt_version"])


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def first_line(command: list[str]) -> str:
    stdout = run(command).stdout.splitlines()
    return stdout[0].strip() if stdout else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitcoind", default=os.environ.get("BITCOIND", "bitcoind"))
    parser.add_argument("--bitcoin-cli", default=os.environ.get("BITCOIN_CLI", "bitcoin-cli"))
    parser.add_argument("--evidence", type=Path, default=Path("bitcoin-core-32-psbt-evidence.json"))
    parser.add_argument(
        "--expected-version-substring",
        default=EXPECTED_VERSION_SUBSTRING,
        help="Required substring in bitcoind --version; use '' only for deliberate non-RC comparison runs.",
    )
    parser.add_argument(
        "--prime-gate-id",
        default=os.environ.get("BC32_PRIME_GATE_ID", "UNSET"),
        help="External PRIME/human authorization reference. UNSET means no claim advancement is permitted.",
    )
    parser.add_argument(
        "--operator",
        default=os.environ.get("BC32_OPERATOR") or os.environ.get("GITHUB_ACTOR") or "UNRECORDED",
        help="Execution operator identity or automation actor.",
    )
    parser.add_argument("--keep-datadir", action="store_true")
    args = parser.parse_args()

    bitcoind = shutil.which(args.bitcoind) or args.bitcoind
    bitcoin_cli = shutil.which(args.bitcoin_cli) or args.bitcoin_cli
    temp_root = Path(tempfile.mkdtemp(prefix="ws-bc32-"))
    datadir = temp_root / "node"
    harness = CoreHarness(bitcoind, bitcoin_cli, datadir)

    observed: dict[str, dict[str, int]] = {}
    technical_result = "INCONCLUSIVE"
    failure: str | None = None
    daemon_version = ""
    cli_version = ""
    chain = None
    network_active = None
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    try:
        daemon_version = first_line([bitcoind, "--version"])
        cli_version = first_line([bitcoin_cli, "--version"])
        if args.expected_version_substring and args.expected_version_substring not in daemon_version:
            raise RuntimeError(
                f"unexpected bitcoind build: expected {args.expected_version_substring!r} in {daemon_version!r}"
            )

        harness.start()
        blockchain_info = harness.cli("getblockchaininfo")
        network_info = harness.cli("getnetworkinfo")
        chain = blockchain_info["chain"]
        network_active = bool(network_info["networkactive"])
        if chain != "regtest" or network_active:
            raise RuntimeError(
                f"isolation check failed: chain={chain!r}, networkactive={network_active!r}"
            )

        wallet = "ws_bc32"
        harness.cli("createwallet", wallet)
        mining_address = harness.cli("getnewaddress", wallet=wallet)
        harness.cli("generatetoaddress", 101, mining_address)

        utxo = harness.cli("listunspent", wallet=wallet)[0]
        destination = harness.cli("getnewaddress", wallet=wallet)
        inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]}]
        outputs = [{destination: 1.0}]

        default_psbt = harness.named("createpsbt", {"inputs": inputs, "outputs": outputs})
        legacy_psbt = harness.named(
            "createpsbt", {"inputs": inputs, "outputs": outputs, "psbt_version": 0}
        )
        observed["createpsbt"] = {
            "default": decode_version(harness, default_psbt),
            "legacy": decode_version(harness, legacy_psbt),
        }

        default_funded = harness.named(
            "walletcreatefundedpsbt",
            {"inputs": inputs, "outputs": outputs},
            wallet=wallet,
        )["psbt"]
        legacy_funded = harness.named(
            "walletcreatefundedpsbt",
            {"inputs": inputs, "outputs": outputs, "psbt_version": 0},
            wallet=wallet,
        )["psbt"]
        observed["walletcreatefundedpsbt"] = {
            "default": decode_version(harness, default_funded),
            "legacy": decode_version(harness, legacy_funded),
        }

        raw_tx = harness.named("createrawtransaction", {"inputs": inputs, "outputs": outputs})
        default_converted = harness.named("converttopsbt", {"hexstring": raw_tx})
        legacy_converted = harness.named(
            "converttopsbt", {"hexstring": raw_tx, "psbt_version": 0}
        )
        observed["converttopsbt"] = {
            "default": decode_version(harness, default_converted),
            "legacy": decode_version(harness, legacy_converted),
        }

        bump_address = harness.cli("getnewaddress", wallet=wallet)
        txid = harness.named(
            "sendtoaddress",
            {"address": bump_address, "amount": 1.0, "replaceable": True},
            wallet=wallet,
        )
        default_bump = harness.named("psbtbumpfee", {"txid": txid}, wallet=wallet)["psbt"]
        legacy_bump = harness.named(
            "psbtbumpfee", {"txid": txid, "psbt_version": 0}, wallet=wallet
        )["psbt"]
        observed["psbtbumpfee"] = {
            "default": decode_version(harness, default_bump),
            "legacy": decode_version(harness, legacy_bump),
        }

        expected = {"default": 2, "legacy": 0}
        technical_result = "PASS" if all(values == expected for values in observed.values()) else "FAIL"
    except Exception as exc:
        technical_result = "FAIL"
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        harness.stop()

    digest_payload = {
        "upstream_tag": PINNED_UPSTREAM_TAG,
        "upstream_commit": PINNED_UPSTREAM_COMMIT,
        "daemon_version": daemon_version,
        "cli_version": cli_version,
        "chain": chain,
        "networkactive": network_active,
        "observed": observed,
        "failure": failure,
        "timestamp_utc": timestamp_utc,
        "prime_gate_id": args.prime_gate_id,
        "operator": args.operator,
    }
    evidence = {
        "benchmark": "bitcoin-core-32",
        "case_id": "BC32-001",
        "upstream": {
            "tag": PINNED_UPSTREAM_TAG,
            "commit": PINNED_UPSTREAM_COMMIT,
            "expected_version_substring": args.expected_version_substring,
            "bitcoind_version": daemon_version,
            "bitcoin_cli_version": cli_version,
        },
        "technical_result": technical_result,
        "claim_class": CASE_CLAIM_CLASS,
        "next_claim_gate": (
            "independent-repeat-and-human-claim-review"
            if technical_result == "PASS"
            else "resolve-failure-before-claim-review"
        ),
        "authorization": {
            "prime_gate_id": args.prime_gate_id,
            "operator": args.operator,
            "timestamp_utc": timestamp_utc,
        },
        "isolation": {
            "chain": chain,
            "networkactive": network_active,
            "real_funds": False,
            "datadir": "disposable",
        },
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "observed_psbt_versions": observed,
        "failure": failure,
        "evidence_digest": sha256_text(json.dumps(digest_payload, sort_keys=True)),
        "note": (
            "A PASS is case-local technical evidence only. Claim advancement requires the external "
            "Worldshepherd authorization, repeatability, and human review gates defined by the benchmark."
        ),
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))

    if not args.keep_datadir:
        shutil.rmtree(temp_root, ignore_errors=True)
    else:
        print(f"kept datadir at {datadir}")

    return 0 if technical_result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
