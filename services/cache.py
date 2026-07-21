"""Simple on-disk JSON cache for HTTP responses (SEC/FMP/FRED).

Keeps us well under SEC rate limits and avoids re-fetching the same filing data.
Keyed by an arbitrary string; values are JSON-serializable. TTL is optional.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

from config.settings import SETTINGS


class JsonCache:
    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.dir = cache_dir or SETTINGS.cache_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.dir / f"{digest}.json"

    def get(self, key: str, ttl_seconds: Optional[float] = None) -> Optional[Any]:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if ttl_seconds is not None:
            age = time.time() - payload.get("_cached_at", 0)
            if age > ttl_seconds:
                return None
        return payload.get("data")

    def set(self, key: str, data: Any) -> None:
        p = self._path(key)
        payload = {"_cached_at": time.time(), "data": data}
        p.write_text(json.dumps(payload), encoding="utf-8")
