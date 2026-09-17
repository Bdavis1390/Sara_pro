from worldshepherd_sara.qx_evidence import digest


def test_digest_is_deterministic_across_key_order():
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})


def test_digest_is_sha256_namespaced():
    value = digest({"evidence": "test"})
    assert value.startswith("sha256:")
    assert len(value) == len("sha256:") + 64
