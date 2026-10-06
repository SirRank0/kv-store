import pytest

from store import KeyValueStore, StoreError


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_set_and_get() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("name", "ada")
    store.set("city", "madison")
    assert store.get("name") == "ada"
    assert store.get("city") == "madison"
    assert store.get("missing") is None


def test_overwrite() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.set("score", "11")
    assert store.get("score") == "11"


def test_ttl_hides_value_after_deadline() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    clock.advance(4.9)
    assert store.get("city") == "madison"
    clock.advance(0.1)
    assert store.get("city") is None
    assert store.get("city") is None


def test_set_without_ttl_clears_old_expiry() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    store.set("city", "madison")
    clock.advance(10)
    assert store.get("city") == "madison"


def test_negative_ttl_rejected() -> None:
    store = KeyValueStore(clock=Clock())
    with pytest.raises(ValueError):
        store.set("city", "madison", ttl=-1)


def test_commit_keeps_writes() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.begin()
    store.set("score", "11")
    store.set("city", "madison")
    store.commit()
    assert store.get("score") == "11"
    assert store.get("city") == "madison"


def test_rollback_restores_previous_values() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.begin()
    store.set("score", "11")
    store.set("score", "12")
    store.set("city", "madison")
    store.rollback()
    assert store.get("score") == "10"
    assert store.get("city") is None


def test_rollback_restores_expiry() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    store.begin()
    store.set("city", "chicago")
    store.rollback()
    assert store.get("city") == "madison"
    clock.advance(5)
    assert store.get("city") is None


def test_rollback_of_write_to_expired_key() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    clock.advance(5)
    assert store.get("city") is None
    store.begin()
    store.set("city", "chicago")
    assert store.get("city") == "chicago"
    store.rollback()
    assert store.get("city") is None


def test_expired_write_inside_transaction_is_hidden_until_rollback() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("score", "10")
    store.begin()
    store.set("score", "11", ttl=3)
    clock.advance(3)
    assert store.get("score") is None
    store.rollback()
    assert store.get("score") == "10"


def test_transaction_state_errors() -> None:
    store = KeyValueStore(clock=Clock())
    with pytest.raises(StoreError):
        store.commit()
    with pytest.raises(StoreError):
        store.rollback()
    store.begin()
    with pytest.raises(StoreError):
        store.begin()
    store.commit()
    with pytest.raises(StoreError):
        store.rollback()
