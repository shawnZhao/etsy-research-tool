import asyncio
import httpx
from app.config import settings
from app.etsy.auth import etsy_auth
from app.etsy.exceptions import (
    EtsyAPIError,
    EtsyRateLimitError,
    EtsyAuthError,
    EtsyNotFoundError,
    EtsyServerError,
)


class EtsyClient:
    def __init__(self):
        self.base_url = settings.etsy_api_base_url
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=etsy_auth.get_headers(),
            timeout=30.0,
        )

    async def close(self):
        await self.client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        for attempt in range(3):
            try:
                response = await self.client.request(method, path, **kwargs)
                return self._handle_response(response)
            except (EtsyRateLimitError, EtsyServerError) as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
            except httpx.RequestError as e:
                if attempt == 2:
                    raise EtsyAPIError(f"Request failed: {e}")
                await asyncio.sleep(2 ** attempt)

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 429:
            raise EtsyRateLimitError("Rate limited", 429)
        if response.status_code in (401, 403):
            raise EtsyAuthError("Authentication failed", response.status_code)
        if response.status_code == 404:
            raise EtsyNotFoundError("Resource not found", 404)
        if response.status_code >= 500:
            raise EtsyServerError("Server error", response.status_code)
        if response.status_code >= 400:
            raise EtsyAPIError(f"API error: {response.text}", response.status_code)
        return response.json()

    async def search_listings(
        self, keyword: str, limit: int = 50, offset: int = 0, sort: str = "score"
    ) -> dict:
        params = {"keywords": keyword, "limit": limit, "offset": offset, "sort_on": sort}
        return await self._request("GET", "/application/listings/active", params=params)

    async def get_listing(self, listing_id: int) -> dict:
        return await self._request("GET", f"/application/listings/{listing_id}")

    async def get_shop(self, shop_id: int) -> dict:
        return await self._request("GET", f"/application/shops/{shop_id}")

    async def get_shop_listings(self, shop_id: int, limit: int = 100, offset: int = 0) -> dict:
        params = {"shop_id": shop_id, "limit": limit, "offset": offset}
        return await self._request("GET", f"/application/shops/{shop_id}/listings/active", params=params)

    async def get_listing_reviews(self, listing_id: int, limit: int = 25, offset: int = 0) -> dict:
        params = {"limit": limit, "offset": offset}
        return await self._request("GET", f"/application/listings/{listing_id}/reviews", params=params)
