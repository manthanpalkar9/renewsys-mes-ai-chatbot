import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class SessionContext:
    last_line: Optional[str] = None
    last_shift: Optional[str] = None
    last_date_expression: Optional[str] = None
    last_kpi: Optional[str] = None
    last_area: Optional[str] = None
    last_intent: Optional[str] = None
    turn_count: int = 0

@dataclass
class ChatSession:
    session_id: str
    user_id: int
    username: str
    role: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[dict] = field(default_factory=list)
    context: SessionContext = field(default_factory=SessionContext)

    def add_message(self, role: str, content: str, metadata: Optional[dict] = None):
        self.history.append({"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat(), "metadata": metadata or {}})
        self.last_activity = datetime.now(timezone.utc)
        self.context.turn_count += 1

    def update_context(self, **kwargs):
        for key, value in kwargs.items():
            if value is not None and hasattr(self.context, key):
                setattr(self.context, key, value)

    def get_context_dict(self) -> dict:
        return {"last_line": self.context.last_line, "last_shift": self.context.last_shift, "last_date_expression": self.context.last_date_expression, "last_kpi": self.context.last_kpi, "last_area": self.context.last_area, "last_intent": self.context.last_intent, "turn_count": self.context.turn_count}

    def get_recent_history(self, max_turns: int = 10) -> list[dict]:
        return self.history[-max_turns * 2:] if self.history else []

    def is_expired(self, timeout_minutes: int = 480) -> bool:
        return (datetime.now(timezone.utc) - self.last_activity) > timedelta(minutes=timeout_minutes)

class SessionManager:
    SESSION_TIMEOUT_MINUTES = 480

    def __init__(self):
        self._sessions: dict[str, ChatSession] = {}

    def create_session(self, user_id: int, username: str, role: str) -> ChatSession:
        session_id = str(uuid.uuid4())
        session = ChatSession(session_id=session_id, user_id=user_id, username=username, role=role)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        session = self._sessions.get(session_id)
        if session and session.is_expired(self.SESSION_TIMEOUT_MINUTES):
            del self._sessions[session_id]
            return None
        return session

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    def cleanup_expired(self):
        expired = [sid for sid, s in self._sessions.items() if s.is_expired(self.SESSION_TIMEOUT_MINUTES)]
        for sid in expired: del self._sessions[sid]

    def get_active_count(self) -> int:
        self.cleanup_expired()
        return len(self._sessions)

session_manager = SessionManager()
