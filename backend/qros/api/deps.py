"""Shared API dependencies: settings, DB sessions, authentication."""
from __future__ import annotations

import secrets
from typing import Iterator, Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import text

from qros.config.settings import Settings

_bearer = HTTPBearer(auto_error=False)


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    s = request.app.state.session_factory()
    try:
        if request.method in ('POST','PUT','PATCH','DELETE') and s.bind.dialect.name=='sqlite':
            s.execute(text('BEGIN IMMEDIATE'))
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def _check(token: Optional[str], settings: Settings) -> str:
    expected = settings.api_token.get_secret_value()
    if not token or not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing token",
                            headers={"WWW-Authenticate": "Bearer"})
    return "owner"


def require_owner(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
                  settings: Settings = Depends(get_app_settings)) -> str:
    return _check(creds.credentials if creds else None, settings)


def require_owner_query(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
                        settings: Settings = Depends(get_app_settings)) -> str:
    """Streaming/download callers use Authorization; secrets are never URL tokens."""
    return _check(creds.credentials if creds else None, settings)
