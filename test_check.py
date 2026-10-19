from check import check_reply, weak_check


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


def test_weak_check_disagrees_on_quoted_population() -> None:
    reply = '{"city": "Rome", "population": "2873000"}'
    assert check_reply(reply) == "broke"
    assert weak_check(reply) == "ok"


def test_weak_check_agrees_on_sentence_and_valid_json() -> None:
    sentence = "Paris is the capital of France."
    assert check_reply(sentence) == "broke"
    assert weak_check(sentence) == "broke"
    valid = '{"city": "Paris", "population": 2100000}'
    assert check_reply(valid) == "ok"
    assert weak_check(valid) == "ok"
