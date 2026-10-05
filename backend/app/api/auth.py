from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_user, get_admin_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.hashed_password):
        logger.info("Failed login attempt for username: {}", request.username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active: raise HTTPException(status_code=403, detail="Account disabled")
    username = user.username
    role_val = user.role.value
    plant_val = user.plant
    line_val = user.line
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("User logged in: username={}", username)
    token = create_access_token(data={"sub": username, "role": role_val, "plant": plant_val, "line": line_val})
    return TokenResponse(access_token=token, token_type="bearer", role=role_val, username=username)

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_user.last_logout_at = datetime.now(timezone.utc)
    await db.commit()
    logger.info("User logged out: username={}", current_user.username)
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
