"""
Renewsys MES AI Chatbot - Main FastAPI Application

SRS References:
  - Section 23: Application Architecture
  - J1: Admin and User roles
  - T1: Login/logout logging
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.database import init_db
from app.api import auth, chat, admin, export

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info(f"Starting Renewsys MES AI Chatbot (Env: {settings.app_env})")
    
    # Initialize internal app database (not MES)
    logger.info("Initializing application database...")
    await init_db()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Renewsys MES AI Chatbot")


app = FastAPI(
    title="Renewsys MES AI Chatbot",
    description="Backend API for the Renewsys MES AI Chatbot (Phase 1)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (for frontend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "online",
        "app_env": settings.app_env,
        "mes_adapter": settings.mes_adapter,
        "llm_provider": settings.llm_provider,
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=settings.debug)
