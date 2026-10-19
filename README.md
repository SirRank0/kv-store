# kv-store

In-memory key-value store.

- `set` / `get`
- `delete`
- `keys_with_prefix`
- expiry stored as a deadline and checked on read
- nested transactions: each begin saves a copy of the whole store

## Reply checks

`check_reply` returns `"ok"` only for a JSON object with a text `city` and a whole-number `population`.

`weak_check` returns `"ok"` if the text merely contains `"city"` and `"population"`.

They disagree on `{"city": "Rome", "population": "2873000"}`. The strict check returns `"broke"` because the population is text. The weak check returns `"ok"`.

```bash
pip install -r requirements.txt
pytest
```
