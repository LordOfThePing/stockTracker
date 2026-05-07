_USD_STABLES = {"USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD", "USDP", "PYUSD"}


def bucket_for(quote_currency: str) -> str:
    """Map a native quote currency to its display bucket.

    USD stablecoins collapse into one 'USD-stables' bucket per kickoff decision.
    Everything else is returned uppercased as its own bucket.
    """
    upper = quote_currency.upper()
    if upper in _USD_STABLES:
        return "USD-stables"
    return upper
