from __future__ import annotations

import hashlib
from pathlib import Path

from config.settings import settings


class PageCacheService:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or settings.CACHE_DIR / "pages"

    def get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()
        return self.cache_dir / f"{url_hash}.txt"

    def load(self, url: str) -> tuple[str | None, Path]:
        cache_path = self.get_cache_path(url)
        if not cache_path.exists():
            return None, cache_path
        return cache_path.read_text(encoding="utf-8"), cache_path

    def save(self, url: str, cleaned_text: str) -> Path:
        cache_path = self.get_cache_path(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(cleaned_text, encoding="utf-8")
        return cache_path
