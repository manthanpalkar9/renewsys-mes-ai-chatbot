from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.user import Base
from app.core.config import settings
import os

_db_url = settings.app_db_url
if _db_url.startswith("sqlite:///"):
    _db_url = _db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

os.makedirs("data", exist_ok=True)

engine = create_async_engine(_db_url, echo=settings.debug)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Automatically ensure default admin user exists
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash

        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin_user = User(
                username="admin",
                email="admin@renewsys.com",
                hashed_password=get_password_hash("admin123!"),
                role=UserRole.ADMIN,
                plant="Khopoli",
                job_role="IT/System Administrator",
            )
            session.add(admin_user)
            await session.commit()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
