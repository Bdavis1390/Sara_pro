"""Externally documented post-quantum proof-of-stake benchmark profiles.

Benchmarks are evidence anchors, not endorsements or claims that a production
mainnet is post-quantum. They are kept separate from Worldshepherd target-family
adapters so testnet evidence cannot silently promote production-chain status.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PqPosBenchmark:
    benchmark_id: str
    network: str
    environment: str
    consensus_family: str
    validator_signature_profile: str
    evidence_state: str
    production_mainnet_pq_consensus: bool
    source_urls: tuple[str, ...]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["source_urls"] = list(self.source_urls)
        return data


BENCHMARKS: dict[str, PqPosBenchmark] = {
    "QRL2_TESTNET": PqPosBenchmark(
        benchmark_id="QRL2_TESTNET",
        network="QRL 2.0 / Project Zond",
        environment="PUBLIC_TESTNET_V2",
        consensus_family="Qrysm beacon-chain proof of stake derived from Ethereum/Prysm architecture",
        validator_signature_profile="ML-DSA-87 validator/attestation signing; official docs state ML-DSA is mandatory for staking validators",
        evidence_state="EXTERNAL_PUBLIC_PQ_POS_TESTNET_BENCHMARK",
        production_mainnet_pq_consensus=False,
        source_urls=(
            "https://test-zond.theqrl.org/testnet/get-started",
            "https://www.theqrl.org/press/qrl-launches-testnet-v2-for-its-postquantum-evmfriendly-blockchain/",
            "https://www.theqrl.org/weekly/",
        ),
    ),
}
