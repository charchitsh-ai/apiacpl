import uuid
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.exceptions import AuthenticationException
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.user import UserRepository

reusable_oauth2 = HTTPBearer(auto_error=False)


async def get_current_user(
    http_auth: HTTPAuthorizationCredentials | None = Depends(reusable_oauth2),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Extracts access token from request header, validates signature and returns the User.
    Raises AuthenticationException on validation failure.
    """
    if not http_auth or not http_auth.credentials:
        raise AuthenticationException(message="Missing authentication credentials.")

    token = http_auth.credentials
    try:
        decoded = security.decode_token(token, is_refresh=False)
        user_id_str = decoded.get("sub")
        if not user_id_str:
            raise AuthenticationException(message="Invalid token payload: Subject missing.")
        user_id = uuid.UUID(user_id_str)
    except Exception:
        raise AuthenticationException(message="Invalid or expired access token.")

    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    if not user:
        raise AuthenticationException(message="User associated with this token does not exist.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensures the authenticated user is marked active."""
    if not current_user.is_active:
        raise AuthenticationException(message="User account is deactivated.")
    return current_user
