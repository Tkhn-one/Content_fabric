"""Сток-провайдеры. picsum — заглушка без ключа (демо); pexels — с ключом заказчика."""
from app.providers.base import StockProvider


class PicsumStock(StockProvider):
    """Заглушка: случайные картинки без API-ключа (для демо-режима)."""

    async def search(self, query: str, n: int = 5, orientation: str = "vertical") -> list[str]:
        return [f"https://picsum.photos/seed/{query.replace(' ', '-')}-{i}/1080/1920" for i in range(n)]


class PexelsStock(StockProvider):
    async def search(self, query: str, n: int = 5, orientation: str = "vertical") -> list[str]:
        raise NotImplementedError("Pexels подключается на этапе 1 (фейслесс-пайплайн)")
