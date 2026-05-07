from decimal import Decimal

import httpx
import pytest

from app.adapters.binance import BinanceAdapter
from app.binance_client import BinanceClient


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/api/v3/time":
        return httpx.Response(200, json={"serverTime": 1700000000000})
    if path == "/api/v3/account":
        # Sanity-check that the signature was attached and the API key header was set.
        assert "signature=" in str(request.url)
        assert request.headers.get("X-MBX-APIKEY") == "FAKEKEY"
        return httpx.Response(200, json={
            "balances": [
                {"asset": "BTC", "free": "0.5", "locked": "0"},
                {"asset": "ETH", "free": "1.0", "locked": "0.5"},
                {"asset": "USDT", "free": "100", "locked": "0"},
                {"asset": "SHIB", "free": "0", "locked": "0"},
                {"asset": "OBSCURE", "free": "5", "locked": "0"},
            ],
        })
    if path == "/api/v3/ticker/price":
        return httpx.Response(200, json=[
            {"symbol": "BTCUSDT", "price": "50000"},
            {"symbol": "ETHUSDT", "price": "3000"},
            {"symbol": "BNBUSDT", "price": "200"},
        ])
    return httpx.Response(404, json={"err": "no fixture", "path": path})


@pytest.mark.asyncio
async def test_fetch_positions_normalizes_account_balances():
    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceClient("FAKEKEY", "FAKESECRET", http_client=http_client)
        adapter = BinanceAdapter(client=client)
        positions = await adapter.fetch_positions()

    by_symbol = {p.symbol: p for p in positions}

    # zero balance excluded
    assert "SHIB" not in by_symbol

    # BTC: free + locked = 0.5
    assert by_symbol["BTC"].quantity == Decimal("0.5")
    assert by_symbol["BTC"].mark_price == Decimal("50000")
    assert by_symbol["BTC"].quote_currency == "USDT"
    assert by_symbol["BTC"].source_venue == "binance"
    assert by_symbol["BTC"].account_label == "spot"
    assert by_symbol["BTC"].price_feed == "binance"
    assert by_symbol["BTC"].feed_symbol == "BTCUSDT"

    # ETH: free + locked = 1.5
    assert by_symbol["ETH"].quantity == Decimal("1.5")
    assert by_symbol["ETH"].mark_price == Decimal("3000")

    # USDT: hardcoded mark of 1
    assert by_symbol["USDT"].quantity == Decimal("100")
    assert by_symbol["USDT"].mark_price == Decimal("1")
    assert by_symbol["USDT"].feed_symbol == "USDT"

    # OBSCURE: held but no USDT pair in tickers -> mark_price is None
    assert by_symbol["OBSCURE"].quantity == Decimal("5")
    assert by_symbol["OBSCURE"].mark_price is None

    # cost basis is never inferred from Binance balances
    for p in positions:
        assert p.cost_basis_per_unit is None
        assert p.cost_basis_currency is None


@pytest.mark.asyncio
async def test_fetch_positions_empty_when_all_balances_zero():
    def empty_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v3/time":
            return httpx.Response(200, json={"serverTime": 1700000000000})
        if path == "/api/v3/account":
            return httpx.Response(200, json={"balances": [
                {"asset": "BTC", "free": "0", "locked": "0"},
            ]})
        return httpx.Response(404)

    transport = httpx.MockTransport(empty_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceClient("K", "S", http_client=http_client)
        adapter = BinanceAdapter(client=client)
        positions = await adapter.fetch_positions()

    assert positions == []


@pytest.mark.asyncio
async def test_disabled_adapter_raises_without_credentials():
    adapter = BinanceAdapter()  # no client, no env keys in test
    with pytest.raises(RuntimeError):
        await adapter.fetch_positions()
