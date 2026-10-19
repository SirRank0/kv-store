"""In-memory key-value store with expiry, nested transactions, and a file.

Values live in a dict, so GET and SET stay one lookup. An expiry is a
deadline stored beside the value and checked on read, not a timer.
Each BEGIN starts an empty undo log. The log records a key's old value
only when that transaction changes it. COMMIT keeps the live store and
moves those notes to the outer log. ROLLBACK writes the notes back.
A path, if given, stores only the committed data as JSON. A restart is a
new store on that path: open transactions are gone.
"""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import threading
import time
from typing import NamedTuple

from sortedcontainers import SortedList


class StoreError(Exception):
    """Raised when a transaction call does not match the current state."""


class _Record(NamedTuple):
    value: str
    expires_at: float | None


class KeyValueStore:
    def __init__(
        self,
        clock: Callable[[], float] | None = None,
        path: str | Path | None = None,
    ) -> None:
        self._clock = clock or time.monotonic
        self._data: dict[str, _Record] = {}
        self._keys: SortedList[str] = SortedList()
        # Newest log is the innermost transaction. A missing key in a log
        # means that transaction has not changed it. A stored None means the
        # key was absent before this transaction changed it.
        self._logs: list[dict[str, _Record | None]] = []
        self._lock = threading.RLock()
        self._path = Path(path) if path is not None else None
        if self._path is not None and self._path.exists():
            self._load()

    def set(self, key: str, value: str, ttl: float | None = None) -> None:
        """Store value under key. ttl is seconds from now, or None to keep it."""
        with self._lock:
            if ttl is not None and ttl < 0:
                raise ValueError("ttl must be >= 0")
            self._note(key)
            is_new = key not in self._data
            expires_at = None if ttl is None else self._clock() + ttl
            self._data[key] = _Record(value, expires_at)
            if is_new:
                self._index_add(key)
            if not self._logs:
                self._save()

    def get(self, key: str) -> str | None:
        """Return the value, or None if the key is missing or expired."""
        with self._lock:
            record = self._data.get(key)
            if record is None:
                return None
            if record.expires_at is not None and self._clock() >= record.expires_at:
                # Leave the record in place during a transaction. A later
                # ROLLBACK restores the noted value, expiry included.
                if not self._logs:
                    del self._data[key]
                    self._index_remove(key)
                    self._save()
                return None
            return record.value

    def begin(self) -> None:
        with self._lock:
            self._logs.append({})

    def commit(self) -> None:
        with self._lock:
            if not self._logs:
                raise StoreError("no transaction open")
            log = self._logs.pop()
            if not self._logs:
                self._save()
                return
            outer = self._logs[-1]
            for key, previous in log.items():
                if key not in outer:
                    outer[key] = previous

    def rollback(self) -> None:
        with self._lock:
            if not self._logs:
                raise StoreError("no transaction open")
            log = self._logs.pop()
            for key, previous in log.items():
                if previous is None:
                    if key in self._data:
                        del self._data[key]
                        self._index_remove(key)
                else:
                    was_missing = key not in self._data
                    self._data[key] = previous
                    if was_missing:
                        self._index_add(key)

    def delete(self, key: str) -> None:
        with self._lock:
            self._note(key)
            if key in self._data:
                del self._data[key]
                self._index_remove(key)
            if not self._logs:
                self._save()

    def _index_add(self, key: str) -> None:
        self._keys.add(key)

    def _index_remove(self, key: str) -> None:
        self._keys.discard(key)

    def _note(self, key: str) -> None:
        if not self._logs:
            return
        log = self._logs[-1]
        if key not in log:
            log[key] = self._data.get(key)

    def _load(self) -> None:
        raw = json.loads(self._path.read_text())
        self._data = {}
        self._keys = SortedList()
        for key, item in raw.items():
            self._data[key] = _Record(item["value"], item["expires_at"])
            self._keys.add(key)
        self._logs = []

    def _save(self) -> None:
        if self._path is None:
            return
        payload = {
            key: {"value": record.value, "expires_at": record.expires_at}
            for key, record in self._data.items()
        }
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload))
        temporary.replace(self._path)

    def keys_with_prefix(self, prefix: str) -> list[str]:
        with self._lock:
            start = self._keys.bisect_left(prefix)
            stop = start
            while stop < len(self._keys) and self._keys[stop].startswith(prefix):
                stop += 1
            # Copy first. get() may drop an expired key from the sorted list.
            matched = self._keys[start:stop]
            return [key for key in matched if self.get(key) is not None]

