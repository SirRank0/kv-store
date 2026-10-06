# kv-store

In-memory key-value store.

- `set` / `get`
- expiry stored as a deadline and checked on read
- one open transaction at a time, with an undo log of the first write to each key

```bash
pip install -r requirements.txt
pytest
```
