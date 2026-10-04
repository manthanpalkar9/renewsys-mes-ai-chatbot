from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.user import User
from app.core.security import decode_access_token, ROLE_ADMIN
from loguru import logger

bearerScheme = HTTPBearer(auto_error=False)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearerScheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    if not credentials: raise credentials_exception
    payload = decode_access_token(credentials.credentials)
    if payload is None: raise credentials_exception
    username: str = payload.get("sub")
    if username is None: raise credentials_exception
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active: raise credentials_exception
    return user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role.value != ROLE_ADMIN: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required for this operation")
    return current_user
