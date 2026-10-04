from fastapi import APIRouter, Depends
from app.models.schemas import SystemStatus
from app.models.user import User
from app.api.deps import get_admin_user
from app.core.config import settings
from app.adapters.jinchen_adapter import get_adapter
from app.services.session_service import session_manager

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/status", response_model=SystemStatus)
async def get_system_status(admin: User = Depends(get_admin_user)):
    adapter = get_adapter(settings.mes_adapter)
    try: db_connected = await adapter.test_connection()
    except: db_connected = False
    return SystemStatus(app_env=settings.app_env, mes_adapter=settings.mes_adapter, llm_provider=settings.llm_provider, db_connected=db_connected, adapter_note="", llm_note="", timezone_note="")

@router.get("/sessions")
async def get_active_sessions(admin: User = Depends(get_admin_user)):
    return {"active_sessions": session_manager.get_active_count()}
