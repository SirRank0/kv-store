import json


def check_reply(reply: str) -> str:
    """Return "ok" if reply is exactly a city/population object, else "broke"."""
    try:
        data = json.loads(reply)
    except json.JSONDecodeError:
        return "broke"
    if (
        isinstance(data, dict)
        and set(data) == {"city", "population"}
        and isinstance(data["city"], str)
        and type(data["population"]) is int
    ):
        return "ok"
    return "broke"


def weak_check(reply: str) -> str:
    """Return "ok" if both field names appear, even when the JSON is invalid."""
    if '"city"' in reply and '"population"' in reply:
        return "ok"
    return "broke"
