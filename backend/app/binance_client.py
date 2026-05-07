"""Low-level Binance HTTP client.

References (https://binance-docs.github.io/apidocs/spot/en/):
  - Endpoint security: signed endpoints use HMAC-SHA256 over the query string
    with the API secret as key, sent as `signature=...`. The API key goes in
    the `X-MBX-APIKEY` header.
  - 418/429 mean rate-limit / IP ban; respect `Retry-After` header.

Read-only access only. Never used to place orders.
"""
import asyncio
import hashlib
import hmac
import logging
import time
import urllib.parse
import httpx

from .redaction import redact_string

logger = logging.getLogger(__name__)


def sign_query(api_secret: str, query_string: str) -> str:
    """HMAC-SHA256 hex digest used as the `signature=` parameter."""
    return hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class BinanceClient:
    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        base_url: str = "https://api.binance.com",
        *,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self._client = http_client
        self._owns_client = http_client is None
        self._time_offset_ms: int = 0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
            self._owns_client = True
        return self._client

    async def close(self) -> None:
        if self._client and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def sync_server_time(self) -> None:
        # https://binance-docs.github.io/apidocs/spot/en/#check-server-time
        client = await self._get_client()
        local_before = int(time.time() * 1000)
        r = await client.get(f"{self.base_url}/api/v3/time")
        r.raise_for_status()
        local_after = int(time.time() * 1000)
        server = r.json()["serverTime"]
        local_mid = (local_before + local_after) // 2
        self._time_offset_ms = server - local_mid

    def _now_ms(self) -> int:
        return int(time.time() * 1000) + self._time_offset_ms

    async def _do_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        client = await self._get_client()
        attempt = 0
        while True:
            r = await client.request(method, url, **kwargs)
            if r.status_code in (418, 429):
                retry_after = float(r.headers.get("Retry-After", "1"))
                attempt += 1
                if attempt > 3:
                    logger.warning("binance giving up after retries: status=%s url=%s", r.status_code, redact_string(url))
                    r.raise_for_status()
                sleep_for = min(max(retry_after, 1.0), 60.0) * (2 ** (attempt - 1))
                logger.info("binance backoff status=%s sleep=%.1fs", r.status_code, sleep_for)
                await asyncio.sleep(sleep_for)
                continue
            r.raise_for_status()
            return r

    async def public_get(self, path: str, params: dict | None = None) -> dict | list:
        r = await self._do_request("GET", f"{self.base_url}{path}", params=params)
        return r.json()

    async def signed_get(self, path: str, params: dict | None = None) -> dict | list:
        # https://binance-docs.github.io/apidocs/spot/en/#signed-trade-user_data-and-margin-endpoints
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Binance signed endpoint requires API key + secret.")
        params = dict(params or {})
        params["timestamp"] = self._now_ms()
        params.setdefault("recvWindow", 5000)
        query = urllib.parse.urlencode(params)
        signature = sign_query(self.api_secret, query)
        url = f"{self.base_url}{path}?{query}&signature={signature}"
        r = await self._do_request("GET", url, headers={"X-MBX-APIKEY": self.api_key})
        return r.json()
