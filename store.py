"""In-memory key-value store with expiry and nested transactions.

Values live in a dict, so GET and SET stay one lookup. An expiry is a
deadline stored beside the value and checked on read, not a timer.
Each BEGIN saves a copy of the whole store. COMMIT drops the newest copy.
ROLLBACK replaces the live store with that copy.
"""

from __future__ import annotations

from collections.abc import Callable
import time
from typing import NamedTuple


class StoreError(Exception):
    """Raised when a transaction call does not match the current state."""


class _Record(NamedTuple):
    value: str
    expires_at: float | None


class KeyValueStore:
    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._data: dict[str, _Record] = {}
        self._snapshots: list[dict[str, _Record]] = []

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        """Store value under key. ttl is seconds from now, or None to keep it."""
        if ttl is not None and ttl < 0:
            raise ValueError("ttl must be >= 0")
        expires_at = None if ttl is None else self._clock() + ttl
        self._data[key] = _Record(value, expires_at)

    def get(self, key: str) -> str | None:
        """Return the value, or None if the key is missing or expired."""
        record = self._data.get(key)
        if record is None:
            return None
        if record.expires_at is not None and self._clock() >= record.expires_at:
            # Leave the record in place during a transaction. ROLLBACK
            # restores the whole snapshot, including a key that has since expired.
            if not self._snapshots:
                del self._data[key]
            return None
        return record.value

    def begin(self) -> None:
        self._snapshots.append(dict(self._data))

    def commit(self) -> None:
        if not self._snapshots:
            raise StoreError("no transaction open")
        self._snapshots.pop()

    def rollback(self) -> None:
        if not self._snapshots:
            raise StoreError("no transaction open")
        self._data = self._snapshots.pop()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        keys = []
        for key in list(self._data):
            if key.startswith(prefix) and self.get(key) is not None:
                keys.append(key)
        return sorted(keys)

