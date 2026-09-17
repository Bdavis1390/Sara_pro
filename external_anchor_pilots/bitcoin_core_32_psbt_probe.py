#!/usr/bin/env python3
"""BC32-001: Bitcoin Core 32 PSBT v2 compatibility probe.

Runs only against an isolated regtest node. It verifies that the four v32 PSBT
creation pathways covered by upstream rpc_psbt.py default to PSBT v2 and still
permit an explicit PSBT v0 request.

No mainnet/testnet connection is used and no real funds are involved.
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
from pathlib import Path
from typing import Any


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, text=True, capture_output=True)


def json_arg(value: Any) -> str:
    if isinstance(value, (dict, list, bool)) or value is None:
        return json.dumps(value, separators=(",", ":"))
    return str(value)


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
        cp = run(cmd)
        text = cp.stdout.strip()
        return json.loads(text) if text else None

    def named(self, method: str, params: dict[str, Any], *, wallet: str | None = None) -> Any:
        cmd = [self.bitcoin_cli, f"-datadir={self.datadir}", "-regtest"]
        if wallet:
            cmd.append(f"-rpcwallet={wallet}")
        cmd.extend(["-named", method])
        for key, value in params.items():
            cmd.append(f"{key}={json_arg(value)}")
        cp = run(cmd)
        text = cp.stdout.strip()
        return json.loads(text) if text else None

    def start(self) -> None:
        self.datadir.mkdir(parents=True, exist_ok=True)
        (self.datadir / "bitcoin.conf").write_text(
            "\n".join(
                [
                    "regtest=1",
                    "server=1",
                    "listen=0",
                    "discover=0",
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
        while time.monotonic() < deadline:
            try:
                self.cli("getblockchaininfo")
                return
            except subprocess.CalledProcessError:
                if self.proc.poll() is not None:
                    raise RuntimeError(f"bitcoind exited early with code {self.proc.returncode}")
                time.sleep(0.25)
        raise TimeoutError("bitcoind did not become RPC-ready within 30 seconds")

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


def decode_version(h: CoreHarness, psbt: str) -> int:
    decoded = h.cli("decodepsbt", psbt)
    return int(decoded["psbt_version"])


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitcoind", default=os.environ.get("BITCOIND", "bitcoind"))
    parser.add_argument("--bitcoin-cli", default=os.environ.get("BITCOIN_CLI", "bitcoin-cli"))
    parser.add_argument("--evidence", type=Path, default=Path("bitcoin-core-32-psbt-evidence.json"))
    parser.add_argument("--keep-datadir", action="store_true")
    args = parser.parse_args()

    bitcoind = shutil.which(args.bitcoind) or args.bitcoind
    bitcoin_cli = shutil.which(args.bitcoin_cli) or args.bitcoin_cli
    temp_root = Path(tempfile.mkdtemp(prefix="ws-bc32-"))
    datadir = temp_root / "node"
    harness = CoreHarness(bitcoind, bitcoin_cli, datadir)

    observed: dict[str, dict[str, int]] = {}
    raw_stdout: list[str] = []
    result = "INCONCLUSIVE"
    failure: str | None = None

    try:
        daemon_version = run([bitcoind, "--version"]).stdout.splitlines()[0].strip()
        cli_version = run([bitcoin_cli, "--version"]).stdout.splitlines()[0].strip()
        raw_stdout.extend([daemon_version, cli_version])

        harness.start()
        wallet = "ws_bc32"
        harness.cli("createwallet", wallet)
        mining_address = harness.cli("getnewaddress", wallet=wallet)
        harness.cli("generatetoaddress", 101, mining_address)

        utxo = harness.cli("listunspent", wallet=wallet)[0]
        destination = harness.cli("getnewaddress", wallet=wallet)
        amount = float(utxo["amount"]) / 2.0
        inputs = [{"txid": utxo["txid"], "vout": utxo["vout"]}]
        outputs = {destination: amount}

        # createpsbt
        default_psbt = harness.named("createpsbt", {"inputs": inputs, "outputs": outputs})
        legacy_psbt = harness.named(
            "createpsbt", {"inputs": inputs, "outputs": outputs, "psbt_version": 0}
        )
        observed["createpsbt"] = {
            "default": decode_version(harness, default_psbt),
            "legacy": decode_version(harness, legacy_psbt),
        }

        # walletcreatefundedpsbt
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

        # converttopsbt
        raw_tx = harness.named("createrawtransaction", {"inputs": inputs, "outputs": outputs})
        default_converted = harness.named("converttopsbt", {"hexstring": raw_tx})
        legacy_converted = harness.named(
            "converttopsbt", {"hexstring": raw_tx, "psbt_version": 0}
        )
        observed["converttopsbt"] = {
            "default": decode_version(harness, default_converted),
            "legacy": decode_version(harness, legacy_converted),
        }

        # psbtbumpfee: create an unconfirmed explicitly replaceable transaction.
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
        result = "PASS" if all(values == expected for values in observed.values()) else "FAIL"
    except Exception as exc:  # evidence should survive a failed probe
        result = "FAIL"
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        harness.stop()

    evidence = {
        "benchmark": "bitcoin-core-32",
        "case_id": "BC32-001",
        "result": result,
        "claim_class": "PROVEN INTERNALLY" if result == "PASS" else "NOT CURRENTLY CLAIMED",
        "isolation": {"network": "regtest-only", "real_funds": False},
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "observed_psbt_versions": observed,
        "failure": failure,
        "stdout_sha256": sha256_text("\n".join(raw_stdout)),
        "note": (
            "A PASS validates only the PSBT version behavior exercised by this pinned local build; "
            "it does not establish third-party wallet compatibility."
        ),
    }
    args.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))

    if not args.keep_datadir:
        shutil.rmtree(temp_root, ignore_errors=True)
    else:
        print(f"kept datadir at {datadir}")

    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
