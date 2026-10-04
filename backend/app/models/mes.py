"""
Normalized MES Data Models.

These models represent the internal application-level view of manufacturing data.
They are strictly decoupled from the actual Jinchen database schema (which is unknown).
Adapters (like MockMESAdapter or future JinchenMESAdapter) are responsible for
translating their specific database results into these normalized models.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import date


class MESProductionRecord(BaseModel):
    """
    A single normalized production record representing a shift/line/area summary.
    This is NOT a database schema.
    """
    record_date: date
    line: str
    shift: str
    area: str
    getin_quantity: int
    departure_quantity: int
    bad_quantity: int
    scrap_quantity: int
    workorder: Optional[str] = None

class MetricResult(BaseModel):
    """The result of a business metric calculation."""
    metric_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    status: str = "success"  # success, definition_required, missing_data, zero_denominator
    message: Optional[str] = None
    formula_note: str = "PROPOSED - REQUIRES BUSINESS VALIDATION"
    calculation_source: str = "BusinessMetricEngine"
