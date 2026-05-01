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
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from Core.Parser.embedder import ChunkEmbedder
from Core.Storage.BucketHandler import BucketHandler
from Core.Storage.PostgresHandler import PostgresHandler

security = HTTPBasic()



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

def require_admin(credentials: Annotated[HTTPBasicCredentials, Depends(security)]) -> None:
    """Raise 401 if the basic auth credentials are wrong."""
    correct_username = secrets.compare_digest(credentials.username, "preppanda")
    correct_password = secrets.compare_digest(credentials.password, "preppass")
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )


# Convenience type aliases
PgDep      = Annotated[PostgresHandler, Depends(get_pg)]
BucketDep  = Annotated[BucketHandler,   Depends(get_bucket)]
EmbedDep   = Annotated[ChunkEmbedder,   Depends(get_embedder)]
AdminDep   = Annotated[None,            Depends(require_admin)]
