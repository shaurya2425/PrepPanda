"""Shared FastAPI dependencies — injected via Depends().

Lifecycle
---------
- Postgres pool, BucketHandler, ChunkEmbedder are created once at startup
  and stored on ``app.state``.
- Each request receives them via ``Depends(get_pg)`` etc.

Admin guard
-----------
- A static ``ADMIN_API_KEY`` env var (``ADMIN_API_KEY``) protects every
  admin route.  The key must be sent in the ``X-Admin-Key`` header.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler


# ─────────────────────────────────────────────────────────────────────
# Dependency getters — pull singletons off app.state
# ─────────────────────────────────────────────────────────────────────

def get_pg(request: Request) -> PostgresHandler:
    return request.app.state.pg


def get_bucket(request: Request) -> BucketHandler:
    return request.app.state.bucket


def get_embedder(request: Request) -> ChunkEmbedder:
    return request.app.state.embedder


# ─────────────────────────────────────────────────────────────────────
# Admin guard
# ─────────────────────────────────────────────────────────────────────

_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")


def require_admin(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    """Raise 403 if the X-Admin-Key header is missing or wrong."""
    if not _ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_API_KEY not configured on the server.",
        )
    if x_admin_key != _ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Admin-Key header.",
        )


# Convenience type aliases
PgDep      = Annotated[PostgresHandler, Depends(get_pg)]
BucketDep  = Annotated[BucketHandler,   Depends(get_bucket)]
EmbedDep   = Annotated[ChunkEmbedder,   Depends(get_embedder)]
AdminDep   = Annotated[None,            Depends(require_admin)]
