"""Pexels: стоковые вертикальные картинки по ключевым словам (ключ заказчика, бесплатно)."""
import httpx

from app.providers.base import StockProvider


class PexelsStock(StockProvider):
    BASE = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, n: int = 5, orientation: str = "vertical") -> list[str]:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                self.BASE,
                params={"query": query, "per_page": n, "orientation": orientation},
                headers={"Authorization": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            urls = [p["src"]["large2x"] for p in data.get("photos", [])]
            return urls[:n]


class PixabayStock(StockProvider):
    async def search(self, query: str, n: int = 5, orientation: str = "vertical") -> list[str]:
        raise NotImplementedError("Pixabay — подключится по необходимости (ключ в настройках)")
