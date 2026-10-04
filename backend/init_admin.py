"""
Initialize the first admin user.
Run this script once to create the initial admin account.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import engine, Base, AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash


async def init_admin():
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        result = await session.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()

        if admin_user:
            print("Admin user already exists.")
            return

        print("Creating initial admin user...")
        # Create admin
        new_admin = User(
            username="admin",
            email="admin@renewsys.com",
            hashed_password=get_password_hash("admin123!"),  # Change in production
            role=UserRole.ADMIN,
            plant="Khopoli",
            job_role="IT/System Administrator",
        )
        session.add(new_admin)
        await session.commit()
        print("Admin user created successfully.")
        print("Username: admin")
        print("Password: admin123!")


if __name__ == "__main__":
    asyncio.run(init_admin())
