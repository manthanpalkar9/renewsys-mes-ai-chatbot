from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import ChatRequest, ChatResponse, SessionInfo
from app.models.user import User
from app.api.deps import get_current_user
from app.services.chat_service import chat_service
from app.services.session_service import session_manager
from datetime import datetime, timezone
from loguru import logger

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest, current_user: User = Depends(get_current_user)):
    if not request.message.strip(): raise HTTPException(status_code=400, detail="Message empty")
    session = session_manager.get_session(request.session_id)
    if not session:
        session = session_manager.create_session(user_id=current_user.id, username=current_user.username, role=current_user.role.value)
        session_manager._sessions[request.session_id] = session
        session_manager._sessions.pop(session.session_id, None)
        session.session_id = request.session_id
    if session.user_id != current_user.id: raise HTTPException(status_code=403, detail="Session access denied")
    response = await chat_service.process_message(message=request.message, session=session, user_role=current_user.role.value)
    return response

@router.post("/session")
async def create_session(current_user: User = Depends(get_current_user)):
    session = session_manager.create_session(user_id=current_user.id, username=current_user.username, role=current_user.role.value)
    return {"session_id": session.session_id, "created_at": session.created_at}

@router.get("/session/{session_id}", response_model=SessionInfo)
async def get_session_info(session_id: str, current_user: User = Depends(get_current_user)):
    session = session_manager.get_session(session_id)
    if not session or session.user_id != current_user.id: raise HTTPException(status_code=404, detail="Not found")
    return SessionInfo(session_id=session.session_id, created_at=session.created_at, message_count=len(session.history), context_summary=str(session.get_context_dict()))

@router.delete("/session/{session_id}")
async def end_session(session_id: str, current_user: User = Depends(get_current_user)):
    session = session_manager.get_session(session_id)
    if session and session.user_id == current_user.id: session_manager.delete_session(session_id)
    return {"message": "Session ended"}
