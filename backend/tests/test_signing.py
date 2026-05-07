import hashlib
import hmac

from app.binance_client import sign_query


def test_sign_query_matches_direct_hmac_sha256():
    secret = "abc"
    msg = "symbol=BTCUSDT&timestamp=1700000000000&recvWindow=5000"
    expected = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    assert sign_query(secret, msg) == expected


def test_sign_query_is_64_hex_chars():
    sig = sign_query("any", "any")
    assert len(sig) == 64
    int(sig, 16)


def test_sign_query_deterministic():
    a = sign_query("s", "q")
    b = sign_query("s", "q")
    assert a == b


def test_sign_query_changes_with_secret():
    assert sign_query("a", "x=1") != sign_query("b", "x=1")


def test_sign_query_changes_with_message():
    assert sign_query("k", "x=1") != sign_query("k", "x=2")


def test_signature_is_never_passed_back_in_logs():
    # sign_query itself returns the signature for use; the redaction layer
    # is what guarantees it never lands in logs. This is just a sanity check
    # that the function returns the digest, not the secret.
    assert "abc" not in sign_query("abc", "x=1")
