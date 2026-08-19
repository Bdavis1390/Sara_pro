import ast
from pathlib import Path

from worldshepherd_sara.quantum_braket_discovery import candidates_as_dict, discover_online_qpus


class FakeBraketClient:
    def __init__(self):
        self.search_calls = []
        self.get_calls = []

    def search_devices(self, **kwargs):
        self.search_calls.append(kwargs)
        if "nextToken" not in kwargs:
            return {
                "devices": [
                    {
                        "deviceArn": "arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1",
                        "deviceName": "Cepheus",
                        "providerName": "Rigetti",
                        "deviceStatus": "ONLINE",
                        "deviceType": "QPU",
                    },
                    {
                        "deviceArn": "arn:aws:braket:us-east-1::device/quantum-simulator/amazon/sv1",
                        "deviceName": "SV1",
                        "providerName": "AWS",
                        "deviceStatus": "ONLINE",
                        "deviceType": "SIMULATOR",
                    },
                ],
                "nextToken": "page-2",
            }
        return {
            "devices": [
                {
                    "deviceArn": "arn:aws:braket:us-west-1::device/qpu/iqm/Garnet",
                    "deviceName": "Garnet",
                    "providerName": "IQM",
                    "deviceStatus": "OFFLINE",
                    "deviceType": "QPU",
                }
            ]
        }

    def get_device(self, **kwargs):
        arn = kwargs["deviceArn"]
        self.get_calls.append(arn)
        assert arn.endswith("Cepheus-1")
        return {
            "deviceArn": arn,
            "deviceName": "Cepheus",
            "providerName": "Rigetti",
            "deviceStatus": "ONLINE",
            "deviceType": "QPU",
            "deviceQueueInfo": [
                {"queue": "QUANTUM_TASKS_QUEUE", "queuePriority": "Normal", "queueSize": "3"}
            ],
            "deviceCapabilities": '{"service":{"executionWindows":[]}}',
        }


def test_discovery_filters_simulators_and_offline_qpus_then_fetches_detail():
    client = FakeBraketClient()
    rows = discover_online_qpus(client, region="us-west-1")
    assert len(rows) == 1
    row = rows[0]
    assert row.provider_name == "Rigetti"
    assert row.device_name == "Cepheus"
    assert row.device_type == "QPU"
    assert row.device_status == "ONLINE"
    assert row.queue_info[0]["queueSize"] == "3"
    assert row.device_capabilities_digest.startswith("sha256:")
    assert row.device_snapshot_digest.startswith("sha256:")
    assert client.search_calls[0] == {"filters": [], "maxResults": 100}
    assert client.search_calls[1]["nextToken"] == "page-2"
    assert len(client.get_calls) == 1


def test_discovery_payload_is_explicitly_not_hardware_evidence():
    rows = discover_online_qpus(FakeBraketClient(), region="us-west-1")
    payload = candidates_as_dict(rows)
    assert payload["candidate_count"] == 1
    assert payload["evidence_class"] == "read_only_braket_qpu_discovery_not_hardware_execution"
    assert "not" in payload["claim_control"].lower()


def test_region_is_required():
    try:
        discover_online_qpus(FakeBraketClient(), region="")
    except ValueError as exc:
        assert "region" in str(exc)
    else:
        raise AssertionError("blank region must fail closed")


def test_discovery_cli_parses_and_exposes_profile_name_not_secret_arguments():
    script = Path("scripts/list_braket_qpu_devices.py").read_text(encoding="utf-8")
    ast.parse(script)
    assert "--aws-profile" in script
    assert "--region" in script
    assert "--output" in script
    assert "--access-key" not in script
    assert "--secret-key" not in script
    assert "aws_secret_access_key" not in script
