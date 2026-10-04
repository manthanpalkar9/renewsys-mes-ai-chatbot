"""
Mock MES Adapter

╔══════════════════════════════════════════════════════════════════════════════╗
║  CONCEPTUAL / MOCK - NOT ACTUAL JINCHEN MES SCHEMA                         ║
║  This schema is used for development only (Track A - Section 24).           ║
║  It does NOT represent actual Jinchen table names, columns, or structure.   ║
║  Real mapping must occur after authorized schema discovery (C1: CONFIRMED). ║
╚══════════════════════════════════════════════════════════════════════════════╝

SRS References:
  - Section 24 (PROPOSED): Two-track delivery, mock data contract
  - C1 (CONFIRMED): Schema must be requested from IT/DBA
  - D1 (CONFIRMED): Shift names A=Morning, B=Second, C=Night
  - D4 (CONFIRMED): Getin = Module entering station
  - D5 (CONFIRMED): Departures = Module leaving station
  - D6 (CONFIRMED): Bad = Module with defect
  - D7 (CONFIRMED): Scrap = Damaged/scrapped module
  - D8 (CONFIRMED): Duplicate barcode scan data quality issue exists
  - D9 (CONFIRMED): Shift=A/B/C, Line=KM1/KM2/KM3
  - L6 (CONFIRMED): Shift times: Morning 07-15, Second 15-23, Night 23-07
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone, date
from typing import Any, Optional
from app.adapters.base import MESAdapterBase, QueryResult, AdapterCapability
from loguru import logger


# ============================================================================
# CONCEPTUAL MOCK DATA
# NOT ACTUAL JINCHEN MES SCHEMA
# These are fictional stand-ins for development/testing only.
# ============================================================================

MOCK_LINES = ["KM1", "KM2", "KM3"]  # D9: CONFIRMED
MOCK_SHIFTS = {                        # D1: CONFIRMED, L6: CONFIRMED
    "A": {"name": "Morning", "start": "07:00", "end": "15:00"},
    "B": {"name": "Second",  "start": "15:00", "end": "23:00"},
    "C": {"name": "Night",   "start": "23:00", "end": "07:00"},
}

# Process areas (D9: Area = Location - confirmed; specific values are CONCEPTUAL)
MOCK_AREAS = ["Glass", "Lamination", "Framing", "Junction Box", "Packing", "Testing"]


def _generate_mock_production_data(days_back: int = 30) -> list[dict]:
    """
    Generate conceptual mock production records.
    CONCEPTUAL ONLY - field names are illustrative, not actual Jinchen columns.
    """
    random.seed(42)  # Reproducible mock data
    records = []
    base_date = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    for day_offset in range(days_back):
        record_date = base_date - timedelta(days=day_offset)
        for line in MOCK_LINES:
            for shift_code, shift_info in MOCK_SHIFTS.items():
                for area in MOCK_AREAS:
                    getin = random.randint(80, 200)      # D4: Getin = module entering station
                    departures = random.randint(75, getin) # D5: Departures = module leaving station
                    bad = random.randint(0, max(1, int(getin * 0.05)))  # D6: Bad = module with defect
                    scrap = random.randint(0, max(1, int(bad * 0.3)))   # D7: Scrap = damaged module

                    records.append({
                        "mock_date": record_date.strftime("%Y-%m-%d"),
                        "mock_line": line,
                        "mock_shift": shift_code,
                        "mock_shift_name": shift_info["name"],
                        "mock_area": area,
                        "mock_getin": getin,
                        "mock_departures": departures,
                        "mock_bad": bad,
                        "mock_scrap": scrap,
                        "mock_workorder": f"WO-{line}-{record_date.strftime('%Y%m%d')}-{shift_code}",
                    })
    return records


# Pre-generate mock data at import time
_MOCK_DATA = _generate_mock_production_data(30)


def _mock_schema_definition() -> dict:
    """
    CONCEPTUAL MOCK SCHEMA DEFINITION
    ===================================
    These table/column names are illustrative stand-ins.
    They do NOT represent actual Jinchen MES tables.
    Real schema must be obtained from IT/DBA (C1: CONFIRMED).
    """
    return {
        "_schema_warning": (
            "CONCEPTUAL / MOCK - NOT ACTUAL JINCHEN MES SCHEMA. "
            "Field names are illustrative only. Real schema pending IT/DBA confirmation (C1)."
        ),
        "tables": {
            "mock_production_events": {
                "description": "CONCEPTUAL: Module production events per shift/line/area",
                "columns": {
                    "mock_date": "DATE - Production date",
                    "mock_line": "VARCHAR - Production line (KM1/KM2/KM3) - D9: CONFIRMED",
                    "mock_shift": "CHAR(1) - Shift code (A/B/C) - D1: CONFIRMED",
                    "mock_shift_name": "VARCHAR - Morning/Second/Night - D1: CONFIRMED",
                    "mock_area": "VARCHAR - Process area/location - D9: Confirmed business term",
                    "mock_getin": "INT - Modules entering station - D4: CONFIRMED",
                    "mock_departures": "INT - Modules leaving station - D5: CONFIRMED",
                    "mock_bad": "INT - Modules with defect - D6: CONFIRMED",
                    "mock_scrap": "INT - Damaged/scrapped modules - D7: CONFIRMED",
                    "mock_workorder": "VARCHAR - Work order identifier - D9: CONFIRMED",
                },
            }
        },
    }


class MockMESAdapter(MESAdapterBase):
    """
    Mock MES Adapter for development and testing.

    CONCEPTUAL / MOCK - NOT ACTUAL JINCHEN MES SCHEMA
    This adapter simulates MES query responses using fictional data.
    It is used exclusively for Track A development (Section 24: PROPOSED).
    """

    ADAPTER_NAME = "MockMESAdapter"
    MOCK_WARNING = (
        "[MOCK DATA] This result is generated from conceptual mock data. "
        "It does NOT reflect real Jinchen MES data or schema."
    )

    async def execute_query(
        self,
        sql: str,
        params: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """
        Execute a query against the mock data.
        Still enforces read-only validation for safety habit building.
        """
        self._validate_read_only(sql)
        logger.debug("MockMESAdapter: Simulating query execution (mock data)")
        await asyncio.sleep(0.05)  # Simulate query latency

        # For the mock adapter, we return a subset of the pre-generated data
        # based on simple heuristics about the SQL content.
        data = _MOCK_DATA
        sql_lower = sql.lower()

        # Apply simple filters based on SQL content
        if "km1" in sql_lower:
            data = [r for r in data if r["mock_line"] == "KM1"]
        elif "km2" in sql_lower:
            data = [r for r in data if r["mock_line"] == "KM2"]
        elif "km3" in sql_lower:
            data = [r for r in data if r["mock_line"] == "KM3"]

        if "shift = 'a'" in sql_lower or "shift='a'" in sql_lower:
            data = [r for r in data if r["mock_shift"] == "A"]
        elif "shift = 'b'" in sql_lower or "shift='b'" in sql_lower:
            data = [r for r in data if r["mock_shift"] == "B"]
        elif "shift = 'c'" in sql_lower or "shift='c'" in sql_lower:
            data = [r for r in data if r["mock_shift"] == "C"]

        # Limit rows
        data = data[:100]

        if not data:
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                adapter_note=self.MOCK_WARNING,
            )

        columns = list(data[0].keys())
        rows = [[r[col] for col in columns] for r in data]

        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            query_time_ms=50.0,
            adapter_note=self.MOCK_WARNING,
        )

    async def test_connection(self) -> bool:
        """Mock adapter is always 'connected'."""
        return True

    def get_capability(self) -> AdapterCapability:
        return AdapterCapability(
            adapter_name=self.ADAPTER_NAME,
            is_mock=True,
            schema_confirmed=False,
            engine_confirmed=False,
            notes=[
                "CONCEPTUAL / MOCK - NOT ACTUAL JINCHEN MES SCHEMA",
                "Used for Track A development only (Section 24: PROPOSED)",
                "Real adapter requires schema from IT/DBA (C1: CONFIRMED)",
                "MES engine unknown (B1: AMBIGUOUS)",
            ],
        )

    async def get_mock_schema_info(self) -> dict:
        return _mock_schema_definition()

    async def get_normalized_data(
        self,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Any]:
        from app.models.mes import MESProductionRecord
        from datetime import datetime
        
        data = _MOCK_DATA
        if line:
            data = [r for r in data if r["mock_line"] == line.upper()]
        if shift:
            data = [r for r in data if r["mock_shift"] == shift.upper()]
        if date_from:
            data = [r for r in data if r["mock_date"] >= str(date_from)]
        if date_to:
            data = [r for r in data if r["mock_date"] <= str(date_to)]
            
        records = []
        for r in data:
            records.append(
                MESProductionRecord(
                    record_date=datetime.strptime(r["mock_date"], "%Y-%m-%d").date(),
                    line=r["mock_line"],
                    shift=r["mock_shift"],
                    area=r["mock_area"],
                    getin_quantity=r["mock_getin"],
                    departure_quantity=r["mock_departures"],
                    bad_quantity=r["mock_bad"],
                    scrap_quantity=r["mock_scrap"],
                    workorder=r["mock_workorder"]
                )
            )
        return records

    def get_aggregated_kpi(
        self,
        kpi_name: str,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """
        Return aggregated KPI values from mock data.
        PROPOSED formulas - REQUIRES BUSINESS VALIDATION (Section 14.2).
        """
        data = _MOCK_DATA

        if line:
            data = [r for r in data if r["mock_line"] == line.upper()]
        if shift:
            data = [r for r in data if r["mock_shift"] == shift.upper()]
        if date_from:
            data = [r for r in data if r["mock_date"] >= str(date_from)]
        if date_to:
            data = [r for r in data if r["mock_date"] <= str(date_to)]

        if not data:
            return {"value": None, "note": "No mock data for selected filters"}

        total_getin = sum(r["mock_getin"] for r in data)
        total_departures = sum(r["mock_departures"] for r in data)
        total_bad = sum(r["mock_bad"] for r in data)
        total_scrap = sum(r["mock_scrap"] for r in data)

        kpi_lower = kpi_name.lower().replace(" ", "_").replace("-", "_")

        # PROPOSED formulas - none are confirmed by Renewsys (Section 14.2)
        FORMULA_DISCLAIMER = "PROPOSED - REQUIRES BUSINESS VALIDATION"

        if kpi_lower in ("total_production", "production"):
            return {"value": total_getin, "unit": "modules", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("get_in_quantity", "getin"):
            return {"value": total_getin, "unit": "modules", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("departure_quantity", "departures"):
            return {"value": total_departures, "unit": "modules", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("bad_quantity", "bad"):
            return {"value": total_bad, "unit": "modules", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("scrap_quantity", "scrap"):
            return {"value": total_scrap, "unit": "modules", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower == "yield":
            if total_getin > 0:
                yield_val = round((total_getin - total_bad) / total_getin * 100, 2)
            else:
                yield_val = None
            return {"value": yield_val, "unit": "%", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("defect_rate", "defect rate"):
            if total_getin > 0:
                defect_rate = round(total_bad / total_getin * 100, 2)
            else:
                defect_rate = None
            return {"value": defect_rate, "unit": "%", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("scrap_rate", "scrap rate"):
            if total_getin > 0:
                scrap_rate = round(total_scrap / total_getin * 100, 2)
            else:
                scrap_rate = None
            return {"value": scrap_rate, "unit": "%", "formula": FORMULA_DISCLAIMER}
        elif kpi_lower in ("process_loss", "process loss"):
            return {
                "value": None,
                "note": "Process loss definition unknown (D11: IDK - TBD). Cannot calculate.",
                "formula": "NOT PROPOSED - depends on unresolved D11",
            }
        elif kpi_lower in ("oee",):
            return {
                "value": None,
                "note": "OEE requires Availability x Performance x Quality. "
                        "Downtime source unconfirmed, Cycle time source unconfirmed (Section 14.2).",
                "formula": FORMULA_DISCLAIMER,
            }
        elif kpi_lower in ("wip",):
            return {
                "value": None,
                "note": "WIP depends on unresolved quantity semantics (D10: IDK - TBD).",
                "formula": "NOT PROPOSED - depends on unresolved D10",
            }
        elif kpi_lower in ("downtime",):
            return {
                "value": None,
                "note": "Downtime source not confirmed (downtime event log existence TBD).",
                "formula": "NOT PROPOSED - source unconfirmed",
            }
        elif kpi_lower in ("cycle_time", "cycle time"):
            return {
                "value": None,
                "note": "Cycle time source not confirmed (process timestamps TBD).",
                "formula": "NOT PROPOSED - source unconfirmed",
            }
        elif kpi_lower in ("first_pass_yield", "first pass yield"):
            return {
                "value": None,
                "note": "First Pass Yield depends on rework loop definition (D12: IDK - TBD).",
                "formula": "NOT PROPOSED - depends on unresolved D12",
            }
        elif kpi_lower in ("rework_rate", "rework rate"):
            return {
                "value": None,
                "note": "Rework rate depends on rework loop definition (D12: IDK - TBD).",
                "formula": "NOT PROPOSED - depends on unresolved D12",
            }
        elif kpi_lower == "throughput":
            return {
                "value": total_departures,
                "unit": "modules",
                "note": "Based on departures; depends on confirmed production definition (TBD).",
                "formula": FORMULA_DISCLAIMER,
            }
        else:
            return {"value": None, "note": f"KPI '{kpi_name}' calculation not yet implemented"}
