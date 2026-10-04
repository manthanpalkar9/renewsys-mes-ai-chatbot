from dataclasses import dataclass
from datetime import datetime, date, timedelta, time
from typing import Optional, Tuple
from app.core.config import settings

SHIFTS = {
    "A": {"name": "Morning", "start_hour": 7,  "end_hour": 15},
    "B": {"name": "Second",  "start_hour": 15, "end_hour": 23},
    "C": {"name": "Night",   "start_hour": 23, "end_hour": 7},
}

SUPPORTED_DATE_EXPRESSIONS = [
    "today", "yesterday", "current_shift", "previous_shift",
    "last_7_days", "last_30_days", "this_week", "last_month",
    "custom_date_range", "custom_time_range",
]

@dataclass
class DateRange:
    date_from: date
    date_to: date
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    shift_code: Optional[str] = None
    shift_name: Optional[str] = None
    expression_used: str = ""
    timezone_note: str = "Timezone TBD"

    def exceeds_limit(self) -> bool:
        return (self.date_to - self.date_from).days > settings.history_days_limit

    def to_dict(self) -> dict:
        return {
            "date_from": str(self.date_from), "date_to": str(self.date_to),
            "time_from": str(self.time_from) if self.time_from else None,
            "time_to": str(self.time_to) if self.time_to else None,
            "shift_code": self.shift_code, "shift_name": self.shift_name,
            "expression": self.expression_used, "timezone_note": self.timezone_note,
        }

class DateService:
    def get_current_date(self) -> date:
        return datetime.now().date()
    def get_current_datetime(self) -> datetime:
        return datetime.now()
    def get_current_shift(self) -> Tuple[str, dict]:
        now = self.get_current_datetime()
        hour = now.hour
        if 7 <= hour < 15: return "A", SHIFTS["A"]
        elif 15 <= hour < 23: return "B", SHIFTS["B"]
        else: return "C", SHIFTS["C"]
    def get_shift_date_range(self, shift_code: str, reference_date: date) -> DateRange:
        shift = SHIFTS.get(shift_code.upper())
        if not shift: raise ValueError(f"Unknown shift code: {shift_code}")
        if shift_code.upper() == "C":
            date_from = reference_date
            date_to = reference_date + timedelta(days=1)
            time_from = time(23, 0)
            time_to = time(7, 0)
        else:
            date_from = date_to = reference_date
            time_from = time(shift["start_hour"], 0)
            time_to = time(shift["end_hour"], 0)
        return DateRange(date_from=date_from, date_to=date_to, time_from=time_from, time_to=time_to, shift_code=shift_code.upper(), shift_name=shift["name"], expression_used=f"shift_{shift_code}")
    def resolve_expression(self, expression: str) -> DateRange:
        today = self.get_current_date()
        expr = expression.lower().replace(" ", "_").replace("-", "_")
        if expr == "today": return DateRange(date_from=today, date_to=today, expression_used="today")
        elif expr == "yesterday": return DateRange(date_from=today - timedelta(days=1), date_to=today - timedelta(days=1), expression_used="yesterday")
        elif expr == "current_shift":
            shift_code, _ = self.get_current_shift()
            return self.get_shift_date_range(shift_code, today)
        elif expr == "previous_shift":
            shift_code, _ = self.get_current_shift()
            shift_order = ["A", "B", "C"]
            prev_idx = (shift_order.index(shift_code) - 1) % 3
            prev_shift = shift_order[prev_idx]
            ref_date = today if prev_shift != "C" else today - timedelta(days=1)
            return self.get_shift_date_range(prev_shift, ref_date)
        elif expr in ("last_7_days", "this_week"): return DateRange(date_from=today - timedelta(days=7), date_to=today, expression_used=expr)
        elif expr in ("last_30_days", "last_month"): return DateRange(date_from=today - timedelta(days=30), date_to=today, expression_used=expr)
        else:
            try:
                from dateutil import parser
                parsed_date = parser.parse(expression, default=datetime.now()).date()
                if parsed_date > today:
                    parsed_date = parsed_date.replace(year=parsed_date.year - 1)
                return DateRange(date_from=parsed_date, date_to=parsed_date, expression_used=expression)
            except Exception:
                raise ValueError(f"Unsupported date expression: {expression}")
    def validate_custom_range(self, date_from: date, date_to: date) -> DateRange:
        if date_from > date_to: raise ValueError("date_from must be before date_to")
        days_span = (date_to - date_from).days
        if days_span > settings.history_days_limit: raise ValueError("Exceeds 30-day limit")
        return DateRange(date_from=date_from, date_to=date_to, expression_used="custom_date_range")
