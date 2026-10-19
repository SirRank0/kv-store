from check import check_reply


def test_ok_replies() -> None:
    assert check_reply('{"city": "Madison", "population": 269840}') == "ok"
    assert check_reply('{"population": 269840, "city": "Madison"}') == "ok"
    assert check_reply('  {"city": "Paris", "population": 0}  ') == "ok"


def test_broke_replies() -> None:
    assert check_reply('The answer is {"city": "Paris", "population": 1}') == "broke"
    assert check_reply('{"city": "Paris"}') == "broke"
    assert check_reply('{"city": "Paris", "population": 1, "extra": 1}') == "broke"
    assert check_reply('{"city": "Paris", "population": "1"}') == "broke"
    assert check_reply('{"city": "Paris", "population": 1.5}') == "broke"
    assert check_reply('{"city": "Paris", "population": true}') == "broke"
    assert check_reply('{"city": 1, "population": 1}') == "broke"
    assert check_reply("[1, 2, 3]") == "broke"
    assert check_reply("not json") == "broke"
