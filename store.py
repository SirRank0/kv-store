"""In-memory key-value store with expiry and single-level transactions.

Values live in a dict, so GET and SET stay one lookup. An expiry is a
deadline stored beside the value and checked on read, not a timer.
A transaction keeps an undo log of the first version of each key written
during that transaction. COMMIT drops the log. ROLLBACK writes it back.
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
        # None means no transaction is open. Otherwise maps a key to the
        # record it had before the first write in this transaction, or None
        # if the key was absent.
        self._undo: dict[str, _Record | None] | None = None

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        """Store value under key. ttl is seconds from now, or None to keep it."""
        if ttl is not None and ttl < 0:
            raise ValueError("ttl must be >= 0")
        self._remember(key)
        expires_at = None if ttl is None else self._clock() + ttl
        self._data[key] = _Record(value, expires_at)

    def get(self, key: str) -> str | None:
        """Return the value, or None if the key is missing or expired."""
        record = self._data.get(key)
        if record is None:
            return None
        if record.expires_at is not None and self._clock() >= record.expires_at:
            # Leave the record in place during a transaction so ROLLBACK can
            # still restore the pre-transaction version.
            if self._undo is None:
                del self._data[key]
            return None
        return record.value

    def begin(self) -> None:
        if self._undo is not None:
            raise StoreError("transaction already open")
        self._undo = {}

    def commit(self) -> None:
        if self._undo is None:
            raise StoreError("no transaction open")
        self._undo = None

    def rollback(self) -> None:
        if self._undo is None:
            raise StoreError("no transaction open")
        for key, previous in self._undo.items():
            if previous is None:
                self._data.pop(key, None)
            else:
                self._data[key] = previous
        self._undo = None

    def _remember(self, key: str) -> None:
        if self._undo is None or key in self._undo:
            return
        self._undo[key] = self._data.get(key)
        
    def delete(self, key: str) -> None:
        self._remember(key)
        self._data.pop(key, None)
