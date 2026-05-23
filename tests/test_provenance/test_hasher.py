"""Test canonical SHA-256 hashing — must be reproducible across runs."""
from opl_cancer.provenance.hasher import hash_claim


def test_hash_is_deterministic_for_same_input() -> None:
    data = {"claim": "test", "pmid": "12345"}
    h1 = hash_claim(data)
    h2 = hash_claim(data)
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == 7 + 64


def test_hash_independent_of_dict_key_order() -> None:
    h1 = hash_claim({"a": 1, "b": 2})
    h2 = hash_claim({"b": 2, "a": 1})
    assert h1 == h2


def test_hash_changes_when_value_changes() -> None:
    h1 = hash_claim({"claim": "test"})
    h2 = hash_claim({"claim": "test2"})
    assert h1 != h2
