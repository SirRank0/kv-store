# kv-store

In-memory key-value store.

- `set` / `get`
- `delete`
- `keys_with_prefix`
- expiry stored as a deadline and checked on read
- nested transactions: each begin starts an empty log of keys that later change
- a path saves committed data as JSON; a restart drops open transactions

## Reply checks

`check_reply` returns `"ok"` only for a JSON object with a text `city` and a whole-number `population`.

`weak_check` returns `"ok"` if the text merely contains `"city"` and `"population"`.

The JSON data `{"city": "Rome", "population": "2873000"}`, when sent through `check_reply`, returns `"broke"` due to `"2873000"` not being detected as a whole number due to the quotations. `weak_check` returns `"ok"` because the text contains the words `"city"` and `"population"`. This difference matters because it shows how implementation of parsing methods can drastically affect the classification of inputs.

```bash
pip install -r requirements.txt
pytest
```
