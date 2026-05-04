"""In-memory cache with temporary file persistence.

The cache lives in RAM for fast reads and is mirrored to ``cache.json``
in the server working directory.  On server start the file is created /
overwritten; on shutdown it is deleted.

Thread safety is provided by an ``asyncio.Lock`` that serialises all
mutations (memory write + file flush).

Usage::

    from Core.cache import cache_store

    # startup
    cache_store.initialize()

    # read-through
    hit = cache_store.get("quizzes", key)
    if hit is None:
        result = await expensive_generation(...)
        await cache_store.put("quizzes", key, result)

    # shutdown
    cache_store.shutdown()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

CACHE_FILE = Path(__file__).resolve().parent.parent / "cache.json"

SECTIONS = ("mindmaps", "notes", "quizzes", "pyqs")


class CacheStore:
    """Global in-memory cache backed by a JSON file."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = {s: {} for s in SECTIONS}
        self._lock = asyncio.Lock()

    # ── lifecycle ────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Create / overwrite cache.json and reset in-memory store."""
        self._data = {s: {} for s in SECTIONS}
        self._flush_sync()
        logger.info("✅ CacheStore initialised  (%s)", CACHE_FILE)

    def shutdown(self) -> None:
        """Delete cache.json and clear memory."""
        self._data = {s: {} for s in SECTIONS}
        try:
            CACHE_FILE.unlink(missing_ok=True)
            logger.info("🗑️  cache.json deleted")
        except OSError as exc:
            logger.warning("Could not delete cache.json: %s", exc)

    # ── key helpers ──────────────────────────────────────────────────

    @staticmethod
    def make_key(*parts: str) -> str:
        """Deterministic SHA-256 hex key from one or more string parts."""
        raw = "|".join(str(p) for p in parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    # ── read / write ─────────────────────────────────────────────────

    def get(self, section: str, key: str) -> Optional[Any]:
        """Return cached value or ``None``.  Always reads from memory."""
        return self._data.get(section, {}).get(key)

    async def put(self, section: str, key: str, value: Any) -> None:
        """Write *value* to memory and flush to disk atomically."""
        async with self._lock:
            if section not in self._data:
                self._data[section] = {}
            self._data[section][key] = value
            self._flush_sync()

    # ── internal ─────────────────────────────────────────────────────

    def _flush_sync(self) -> None:
        """Persist current memory state to cache.json (atomic write)."""
        tmp = CACHE_FILE.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, default=str)
            tmp.replace(CACHE_FILE)
        except OSError as exc:
            logger.error("cache.json flush failed: %s", exc)


# ── singleton ────────────────────────────────────────────────────────
cache_store = CacheStore()
