from app.redaction import redact_string, redact_mapping


def test_redact_string_strips_known_query_params():
    s = "GET /api/v3/account?timestamp=1&apiKey=ABC&signature=DEADBEEF"
    out = redact_string(s)
    assert "ABC" not in out
    assert "DEADBEEF" not in out
    assert "REDACTED" in out


def test_redact_mapping_strips_sensitive_keys():
    payload = {
        "apiKey": "ABC",
        "secret": "shhh",
        "X-MBX-APIKEY": "headerval",
        "balances": [{"asset": "BTC", "free": "1"}],
    }
    out = redact_mapping(payload)
    assert out["apiKey"] == "REDACTED"
    assert out["secret"] == "REDACTED"
    assert out["X-MBX-APIKEY"] == "REDACTED"
    assert out["balances"] == [{"asset": "BTC", "free": "1"}]


def test_redact_mapping_recurses_into_strings():
    payload = {"url": "https://x?signature=DEADBEEF"}
    out = redact_mapping(payload)
    assert "DEADBEEF" not in out["url"]
