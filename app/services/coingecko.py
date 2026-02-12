"""CoinGecko API client with in-memory caching to avoid rate limits."""
import httpx
import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)


class CoinGeckoClient:
    """Client for interacting with CoinGecko API with built-in caching."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    CACHE_TTL = 60  # seconds

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._cache: Dict[str, float] = {}
        self._cache_timestamp: float = 0

    def _is_cache_valid(self) -> bool:
        return (time.time() - self._cache_timestamp) < self.CACHE_TTL and bool(
            self._cache
        )

    async def get_prices(self, coin_ids: List[str]) -> Dict[str, float]:
        """
        Fetch current prices for multiple cryptocurrencies.
        Uses a 60-second in-memory cache to avoid CoinGecko rate limits.
        """
        if not coin_ids:
            return {}

        coin_ids = list(set(c.lower().strip() for c in coin_ids))

        if self._is_cache_valid():
            all_cached = all(cid in self._cache for cid in coin_ids)
            if all_cached:
                return {cid: self._cache[cid] for cid in coin_ids}

        ids_param = ",".join(coin_ids)

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/simple/price",
                params={"ids": ids_param, "vs_currencies": "usd"},
            )
            response.raise_for_status()
            data = response.json()

            prices = {}
            for coin_id in coin_ids:
                if coin_id in data and "usd" in data[coin_id]:
                    price = data[coin_id]["usd"]
                    prices[coin_id] = price
                    self._cache[coin_id] = price
                else:
                    prices[coin_id] = self._cache.get(coin_id, 0.0)

            self._cache_timestamp = time.time()
            return prices

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("CoinGecko rate limit hit — using cached prices")
                return {cid: self._cache.get(cid, 0.0) for cid in coin_ids}
            logger.error(f"Error fetching prices from CoinGecko: {e}")
            return {cid: self._cache.get(cid, 0.0) for cid in coin_ids}

        except httpx.HTTPError as e:
            logger.error(f"Error fetching prices from CoinGecko: {e}")
            return {cid: self._cache.get(cid, 0.0) for cid in coin_ids}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
coingecko_client = CoinGeckoClient()
