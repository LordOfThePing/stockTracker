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
        assert "signature=" in str(request.url)
        assert request.headers.get("X-MBX-APIKEY") == "FAKEKEY"
        return httpx.Response(200, json={
            "balances": [
                {"asset": "BTC", "free": "0.5", "locked": "0"},
                {"asset": "ETH", "free": "1.0", "locked": "0.5"},
                {"asset": "USDT", "free": "100", "locked": "0"},
                {"asset": "ARS", "free": "5000", "locked": "0"},
                {"asset": "SHIB", "free": "0", "locked": "0"},
                {"asset": "OBSCURE", "free": "5", "locked": "0"},
            ],
        })
    if path == "/sapi/v1/asset/get-funding-asset":
        assert request.method == "POST"
        assert "signature=" in str(request.url)
        assert request.headers.get("X-MBX-APIKEY") == "FAKEKEY"
        return httpx.Response(200, json=[
            {"asset": "ETH", "free": "2.0", "locked": "0", "freeze": "0", "withdrawing": "0"},
            {"asset": "SOL", "free": "10", "locked": "0", "freeze": "0", "withdrawing": "0"},
        ])
    if path == "/api/v3/ticker/price":
        return httpx.Response(200, json=[
            {"symbol": "BTCUSDT", "price": "50000"},
            {"symbol": "ETHUSDT", "price": "3000"},
            {"symbol": "SOLUSDT", "price": "150"},
            {"symbol": "BNBUSDT", "price": "200"},
        ])
    return httpx.Response(404, json={"err": "no fixture", "path": path})


@pytest.mark.asyncio
async def test_fetch_positions_normalizes_spot_and_funding_balances():
    transport = httpx.MockTransport(_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceClient("FAKEKEY", "FAKESECRET", http_client=http_client)
        adapter = BinanceAdapter(client=client)
        positions = await adapter.fetch_positions()

    by_key = {(p.account_label, p.symbol): p for p in positions}

    # zero balance excluded
    assert ("spot", "SHIB") not in by_key

    # Spot BTC: free + locked = 0.5
    assert by_key[("spot", "BTC")].quantity == Decimal("0.5")
    assert by_key[("spot", "BTC")].mark_price == Decimal("50000")
    assert by_key[("spot", "BTC")].quote_currency == "USDT"
    assert by_key[("spot", "BTC")].source_venue == "binance"
    assert by_key[("spot", "BTC")].price_feed == "binance"
    assert by_key[("spot", "BTC")].feed_symbol == "BTCUSDT"

    # Spot ETH: free + locked = 1.5
    assert by_key[("spot", "ETH")].quantity == Decimal("1.5")
    assert by_key[("spot", "ETH")].mark_price == Decimal("3000")

    # Funding ETH: 2.0 — separate row from Spot ETH
    assert by_key[("funding", "ETH")].quantity == Decimal("2.0")
    assert by_key[("funding", "ETH")].mark_price == Decimal("3000")

    # Funding SOL: 10 — only in Funding wallet
    assert by_key[("funding", "SOL")].quantity == Decimal("10")
    assert by_key[("funding", "SOL")].mark_price == Decimal("150")
    assert ("spot", "SOL") not in by_key

    # USDT in Spot: hardcoded mark of 1, USD-stables bucket
    assert by_key[("spot", "USDT")].quantity == Decimal("100")
    assert by_key[("spot", "USDT")].mark_price == Decimal("1")
    assert by_key[("spot", "USDT")].quote_currency == "USDT"
    assert by_key[("spot", "USDT")].feed_symbol == "USDT"

    # ARS: fiat — own bucket, mark=1, quote_currency=ARS (NOT USDT)
    ars = by_key[("spot", "ARS")]
    assert ars.quantity == Decimal("5000")
    assert ars.quote_currency == "ARS"
    assert ars.mark_price == Decimal("1")
    assert ars.feed_symbol == "ARS"
    assert ars.asset_type == "other"

    # OBSCURE: held but no USDT pair -> mark_price is None, quote stays USDT
    assert by_key[("spot", "OBSCURE")].quantity == Decimal("5")
    assert by_key[("spot", "OBSCURE")].mark_price is None
    assert by_key[("spot", "OBSCURE")].quote_currency == "USDT"

    # cost basis is never inferred from Binance balances
    for p in positions:
        assert p.cost_basis_per_unit is None
        assert p.cost_basis_currency is None


@pytest.mark.asyncio
async def test_funding_wallet_failure_does_not_block_spot():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v3/time":
            return httpx.Response(200, json={"serverTime": 1700000000000})
        if path == "/api/v3/account":
            return httpx.Response(200, json={"balances": [
                {"asset": "BTC", "free": "0.1", "locked": "0"},
            ]})
        if path == "/sapi/v1/asset/get-funding-asset":
            return httpx.Response(500, json={"err": "boom"})
        if path == "/api/v3/ticker/price":
            return httpx.Response(200, json=[{"symbol": "BTCUSDT", "price": "50000"}])
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = BinanceClient("K", "S", http_client=http_client)
        adapter = BinanceAdapter(client=client)
        positions = await adapter.fetch_positions()

    assert len(positions) == 1
    assert positions[0].account_label == "spot"
    assert positions[0].symbol == "BTC"


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
