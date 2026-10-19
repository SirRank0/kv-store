"""In-memory key-value store with expiry and nested transactions.

Values live in a dict, so GET and SET stay one lookup. An expiry is a
deadline stored beside the value and checked on read, not a timer.
Each BEGIN starts an empty undo log. The log records a key's old value
only when that transaction changes it. COMMIT keeps the live store and
moves those notes to the outer log. ROLLBACK writes the notes back.
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
        # Newest log is the innermost transaction. A missing key in a log
        # means that transaction has not changed it. A stored None means the
        # key was absent before this transaction changed it.
        self._logs: list[dict[str, _Record | None]] = []

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        """Store value under key. ttl is seconds from now, or None to keep it."""
        if ttl is not None and ttl < 0:
            raise ValueError("ttl must be >= 0")
        self._note(key)
        expires_at = None if ttl is None else self._clock() + ttl
        self._data[key] = _Record(value, expires_at)

    def get(self, key: str) -> str | None:
        """Return the value, or None if the key is missing or expired."""
        record = self._data.get(key)
        if record is None:
            return None
        if record.expires_at is not None and self._clock() >= record.expires_at:
            # Leave the record in place during a transaction. A later
            # ROLLBACK restores the noted value, expiry included.
            if not self._logs:
                del self._data[key]
            return None
        return record.value

    def begin(self) -> None:
        self._logs.append({})

    def commit(self) -> None:
        if not self._logs:
            raise StoreError("no transaction open")
        log = self._logs.pop()
        if not self._logs:
            return
        outer = self._logs[-1]
        for key, previous in log.items():
            if key not in outer:
                outer[key] = previous

    def rollback(self) -> None:
        if not self._logs:
            raise StoreError("no transaction open")
        log = self._logs.pop()
        for key, previous in log.items():
            if previous is None:
                self._data.pop(key, None)
            else:
                self._data[key] = previous

    def delete(self, key: str) -> None:
        self._note(key)
        self._data.pop(key, None)

    def _note(self, key: str) -> None:
        if not self._logs:
            return
        log = self._logs[-1]
        if key not in log:
            log[key] = self._data.get(key)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        keys = []
        for key in list(self._data):
            if key.startswith(prefix) and self.get(key) is not None:
                keys.append(key)
        return sorted(keys)

