from app.currency import bucket_for


def test_usd_stables_collapse_into_one_bucket():
    for stable in ("USDT", "USDC", "BUSD", "FDUSD", "DAI"):
        assert bucket_for(stable) == "USD-stables"


def test_non_stables_keep_their_own_bucket():
    assert bucket_for("ARS") == "ARS"
    assert bucket_for("BTC") == "BTC"
    assert bucket_for("USD") == "USD"


def test_lowercase_input_normalized():
    assert bucket_for("usdt") == "USD-stables"
    assert bucket_for("ars") == "ARS"
