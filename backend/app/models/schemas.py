from pydantic import BaseModel, Field
from typing import Optional, Any, Literal
from datetime import datetime
from enum import Enum

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None
    role: str = "user"
    plant: Optional[str] = "Khopoli"
    area: Optional[str] = None
    line: Optional[str] = None
    job_role: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    plant: Optional[str]
    area: Optional[str]
    line: Optional[str]
    job_role: Optional[str]
    created_at: datetime
    last_login_at: Optional[datetime]
    model_config = {"from_attributes": True}

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    session_id: str
    message: str

class DataType(str, Enum):
    MEASURED = "measured"
    CALCULATED = "calculated"
    ANALYTICAL = "analytical"
    PREDICTIVE = "predictive"

class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"
    TREND = "trend"

class ChartData(BaseModel):
    chart_type: ChartType
    title: str
    labels: list[str]
    datasets: list[dict]
    options: Optional[dict] = None

class KPICard(BaseModel):
    kpi_name: str
    value: Any
    unit: Optional[str] = None
    period: Optional[str] = None
    line: Optional[str] = None
    shift: Optional[str] = None
    data_type: DataType = DataType.MEASURED
    formula_note: str = "PROPOSED - REQUIRES BUSINESS VALIDATION"
    is_formula_confirmed: bool = False

class TableData(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total_rows: int

class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    answer: str
    response_type: Literal["text", "table", "kpi_card", "chart", "clarification", "error"]
    data_type: Optional[DataType] = None
    table: Optional[TableData] = None
    kpi_card: Optional[KPICard] = None
    chart: Optional[ChartData] = None
    data_freshness: Optional[str] = None
    last_updated: Optional[datetime] = None
    generated_sql: Optional[str] = None
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    message_count: int
    context_summary: Optional[str] = None

class SystemStatus(BaseModel):
    app_env: str
    mes_adapter: str
    llm_provider: str
    db_connected: bool
    adapter_note: str
    llm_note: str
    timezone_note: str
