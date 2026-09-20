from typing import Annotated

import jwt
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

bearer = HTTPBearer(auto_error=False)


def _claims(credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)]) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        return jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "iss", "iat", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc


def require_user(claims: Annotated[dict, Security(_claims)]) -> dict:
    return claims


def require_admin(claims: Annotated[dict, Security(_claims)]) -> dict:
    if "ADMIN" not in claims.get("roles", []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return claims


def require_internal(x_internal_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")
