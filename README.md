# kv-store

In-memory key-value store.

- `set` / `get`
- `delete`
- `keys_with_prefix`
- expiry stored as a deadline and checked on read
- nested transactions: each begin starts an empty log of keys that later change
- a path saves committed data as JSON; a restart drops open transactions

## Design notes

**Undo logs instead of full copies.**  
Each `begin` starts an empty log. The log only records a key the first time that transaction changes it, storing the previous value (or `None` if the key was absent). `commit` merges the log into the outer transaction (or saves to disk if it is the outermost). `rollback` writes the recorded values back. This keeps `begin` cheap and only pays for the keys that actually change.

**Expiry is checked on read.**  
A key stores a deadline next to its value. `get` returns `None` and removes the key if the deadline has passed and no transaction is open. During an open transaction the record is left in place so a later `rollback` can still restore the pre-transaction version. Expired keys are also filtered out of `keys_with_prefix`.

**Sorted index for prefix search.**  
Keys are kept in a `SortedList`. `keys_with_prefix` uses binary search to find the start of the matching range, then walks only that range. This avoids scanning every key when the store is large.

**RLock for concurrency.**  
Public methods take a re-entrant lock. This lets `keys_with_prefix` call `get` without deadlocking, while still protecting the data and the index from concurrent writers.

**Persistence.**  
If a path is given, only committed data is written to a JSON file (atomic temp-file replace). Open transactions are discarded on restart; the new store loads only the last committed state.

## Reply checks

`check_reply` returns `"ok"` only for a JSON object with a text `city` and a whole-number `population`.

`weak_check` returns `"ok"` if the text merely contains `"city"` and `"population"`.

The JSON data `{"city": "Rome", "population": "2873000"}`, when sent through `check_reply`, returns `"broke"` due to `"2873000"` not being detected as a whole number due to the quotations. `weak_check` returns `"ok"` because the text contains the words `"city"` and `"population"`. This difference matters because it shows how implementation of parsing methods can drastically affect the classification of inputs.

```bash
pip install -r requirements.txt
pytest
```
