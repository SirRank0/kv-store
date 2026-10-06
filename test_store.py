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


def test_delete_removes_one_key() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.set("city", "madison")
    store.delete("score")
    assert store.get("score") is None
    assert store.get("city") == "madison"


def test_delete_missing_or_twice_does_not_raise() -> None:
    store = KeyValueStore(clock=Clock())
    store.delete("missing")
    store.set("score", "10")
    store.delete("score")
    store.delete("score")
    assert store.get("score") is None


def test_delete_expired_key_does_not_raise() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    clock.advance(5)
    store.delete("city")
    assert store.get("city") is None


def test_delete_then_rollback_restores_value_and_expiry() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    store.begin()
    store.delete("city")
    assert store.get("city") is None
    store.rollback()
    assert store.get("city") == "madison"
    clock.advance(5)
    assert store.get("city") is None


def test_delete_then_commit_stays_deleted() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.begin()
    store.delete("score")
    store.commit()
    assert store.get("score") is None


def test_delete_then_set_rollback_restores_original() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.begin()
    store.delete("score")
    store.set("score", "11")
    assert store.get("score") == "11"
    store.rollback()
    assert store.get("score") == "10"


def test_key_created_in_transaction_then_deleted() -> None:
    store = KeyValueStore(clock=Clock())
    store.begin()
    store.set("score", "10")
    store.delete("score")
    store.rollback()
    assert store.get("score") is None

    store = KeyValueStore(clock=Clock())
    store.begin()
    store.set("score", "10")
    store.delete("score")
    store.commit()
    assert store.get("score") is None


def test_delete_does_not_open_a_transaction() -> None:
    store = KeyValueStore(clock=Clock())
    store.delete("score")
    store.begin()
    with pytest.raises(StoreError):
        store.begin()


def test_keys_with_prefix_matches_and_sorts() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.set("city", "madison")
    store.set("school", "east")
    store.set("City", "austin")
    assert store.keys_with_prefix("s") == ["school", "score"]
    assert store.keys_with_prefix("sco") == ["score"]
    assert store.keys_with_prefix("") == ["City", "city", "school", "score"]
    assert store.keys_with_prefix("z") == []
    assert store.keys_with_prefix("c") == ["city"]
    assert store.keys_with_prefix("C") == ["City"]


def test_keys_with_prefix_omits_expired_and_deleted() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    store.set("score", "10")
    store.set("school", "east")
    clock.advance(5)
    assert store.keys_with_prefix("") == ["school", "score"]
    store.delete("score")
    assert store.keys_with_prefix("s") == ["school"]


def test_keys_with_prefix_sees_open_transaction() -> None:
    store = KeyValueStore(clock=Clock())
    store.set("score", "10")
    store.set("school", "east")
    store.begin()
    store.delete("score")
    store.set("stem", "yes")
    assert store.keys_with_prefix("s") == ["school", "stem"]
    store.rollback()
    assert store.keys_with_prefix("s") == ["school", "score"]

    store.begin()
    store.delete("score")
    store.commit()
    assert store.keys_with_prefix("s") == ["school"]


def test_keys_with_prefix_omits_key_expired_inside_transaction() -> None:
    clock = Clock()
    store = KeyValueStore(clock=clock)
    store.set("city", "madison", ttl=5)
    store.set("score", "10")
    store.begin()
    clock.advance(5)
    assert store.keys_with_prefix("") == ["score"]
    store.rollback()
    assert store.get("city") is None
