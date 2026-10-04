from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone
import enum

class Base(DeclarativeBase): pass

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.USER)
    is_active = Column(Boolean, default=True, nullable=False)
    plant = Column(String(50), nullable=True, default="Khopoli")
    area = Column(String(100), nullable=True)
    line = Column(String(20), nullable=True)
    job_role = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime, nullable=True)
    last_logout_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User username={self.username} role={self.role}>"
