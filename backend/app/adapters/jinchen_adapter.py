"""
Jinchen MES REST API Adapter

Implements the real MES integration layer for Jinchen MES based on Phase 3 Technical Discovery.
Communicates via HTTP REST endpoints (port 8000), fetches raw production and defect events,
normalizes records into MESProductionRecord, and delivers them to the deterministic BusinessMetricEngine.

SRS References:
  - F2 (CONFIRMED): Read-only operations strictly enforced.
  - F6 (CONFIRMED): Authenticated read-only access via Bearer token.
  - D9 (CONFIRMED): Production lines (KM1/KM2/KM3/RenK-1/RenK-2/Line 3/Line 4).
  - D1, L6 (CONFIRMED): Shifts A (07-15), B (15-23), C (23-07).
  - Section 23.2: MESAdapter abstraction pattern.
"""

import httpx
from datetime import datetime, date, timedelta, time
from typing import Optional, Any
from loguru import logger

from app.adapters.base import MESAdapterBase, QueryResult, AdapterCapability
from app.models.mes import MESProductionRecord
from app.core.config import settings


# Confirmed Line ID Dictionary (Jinchen MES Int64 IDs)
JINCHEN_LINE_IDS: dict[str, int] = {
    "KM1": 738616585908229,
    "LINE 1": 738616585908229,
    "LINE1": 738616585908229,
    "RENK-1": 738616585908229,
    "KM2": 738620881702917,
    "LINE 2": 738620881702917,
    "LINE2": 738620881702917,
    "RENK-2": 738620881702917,
    "KM3": 738620932063237,
    "LINE 3": 738620932063237,
    "LINE3": 738620932063237,
    "RENK-3": 738620932063237,
    "LINE 4": 764804556390405,
    "LINE4": 764804556390405,
    "PDI": 764804556390405,
    "RENK-PDI": 764804556390405,
}

# Reverse Line Map for normalizing responses back to standardized line names
JINCHEN_LINE_REVERSE: dict[int, str] = {
    738616585908229: "KM1",
    738620881702917: "KM2",
    738620932063237: "KM3",
    764804556390405: "PDI",
}

# Confirmed Shift Schedules
SHIFT_SCHEDULES = {
    "A": {"start": time(7, 0, 0), "end": time(15, 0, 0), "crosses_midnight": False},
    "B": {"start": time(15, 0, 0), "end": time(23, 0, 0), "crosses_midnight": False},
    "C": {"start": time(23, 0, 0), "end": time(7, 0, 0), "crosses_midnight": True},
}


class JinchenMESAdapter(MESAdapterBase):
    """
    Production REST API adapter for Jinchen MES.
    
    Interfaces:
      1. LotFinalDataReport (POST /api/app/report/756398601302021/data):
         Provides completed production output and finished module records.
      2. DefectData (POST /api/app/report/787763718877829/data):
         Provides defect records and deduplicated bad quantities (Type="0").
      3. QueryLotReport (POST /api/app/lot/lots):
         Provides station WIP and lot queue tracking.
    """

    ADAPTER_NAME = "JinchenMESAdapter"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = (base_url or getattr(settings, "jinchen_api_url", "http://10.69.12.10:8000")).rstrip("/")
        self.api_token = api_token or getattr(settings, "jinchen_api_token", None)
        self.timeout = timeout or getattr(settings, "jinchen_api_timeout", 30.0)

    def _get_headers(self, route: str) -> dict[str, str]:
        """Construct standard HTTP headers required by Jinchen MES ASP.NET backend."""
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "X-Button-Permission": "Search",
            "Route": route,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}{route}",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _resolve_line_id(self, line: Optional[str]) -> Optional[int]:
        """Map human or normalized line name to Jinchen 64-bit line ID."""
        if not line:
            return None
        return JINCHEN_LINE_IDS.get(line.upper().strip())

    def _get_shift_window(self, ref_date: date, shift: str) -> tuple[str, str]:
        """Calculate exact StartDate and EndDate strings (YYYY-MM-DD HH:mm:ss) for a shift."""
        shift_key = shift.upper().strip()
        sched = SHIFT_SCHEDULES.get(shift_key)
        if not sched:
            # Default to whole calendar day
            return (
                f"{ref_date.strftime('%Y-%m-%d')} 00:00:00",
                f"{ref_date.strftime('%Y-%m-%d')} 23:59:59",
            )

        start_dt = datetime.combine(ref_date, sched["start"])
        if sched["crosses_midnight"]:
            end_dt = datetime.combine(ref_date + timedelta(days=1), sched["end"])
        else:
            end_dt = datetime.combine(ref_date, sched["end"])

        return (
            start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        )

    async def test_connection(self) -> bool:
        """Test HTTP connectivity to Jinchen MES host."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(self.base_url)
                return resp.status_code < 500
        except Exception as e:
            logger.warning(f"Jinchen MES connection test failed: {e}")
            return False

    def get_capability(self) -> AdapterCapability:
        return AdapterCapability(
            adapter_name=self.ADAPTER_NAME,
            is_mock=False,
            schema_confirmed=True,
            engine_confirmed=True,
            notes=[
                "Live Jinchen MES REST API Adapter",
                "Host: 10.69.12.10:8000 (HTTP REST)",
                "Production: LotFinalDataReport (/api/app/report/756398601302021/data)",
                "Defects: DefectData Report (/api/app/report/787763718877829/data)",
                "Lot Queues: QueryLotReport (/api/app/lot/lots)",
                "Auth: OAuth2 / OpenID Connect Bearer Token",
            ],
        )

    async def get_mock_schema_info(self) -> dict:
        """Return catalog of discovered Jinchen MES API interfaces."""
        return {
            "adapter": self.ADAPTER_NAME,
            "base_url": self.base_url,
            "endpoints": {
                "lot_final_data": "/api/app/report/756398601302021/data",
                "defect_data": "/api/app/report/787763718877829/data",
                "lot_query": "/api/app/lot/lots",
            },
            "line_ids": JINCHEN_LINE_IDS,
        }

    async def execute_query(
        self,
        sql: str,
        params: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """
        Enforce safety and execute virtual queries via adapter.
        Phase 1 enforces SELECT-only read access.
        """
        self._validate_read_only(sql)
        return QueryResult(
            columns=["status", "message"],
            rows=[["ACTIVE", "Jinchen MES REST adapter active. Use get_normalized_data() for metric engine."]],
            row_count=1,
            data_freshness_note="Real-time MES REST API",
            adapter_note="JinchenMESAdapter read-only REST pipeline",
        )

    async def fetch_production_summary(
        self,
        start_date: str,
        end_date: str,
        line_id: Optional[int] = None,
        page_size: int = 5000,
    ) -> dict[str, Any]:
        """
        Query LotFinalDataReport (POST /api/app/report/756398601302021/data).
        Returns completed production modules.
        """
        url = f"{self.base_url}/api/app/report/756398601302021/data"
        route = "/RPT-ReportManagement/ProductionReport/LotFinalDataReport"

        filters = [
            {"Field": "StartDate", "Operator": "Equal", "Value": start_date},
            {"Field": "EndDate", "Operator": "Equal", "Value": end_date},
        ]
        if line_id is not None:
            filters.append({"Field": "LineCode", "Operator": "Equal", "Value": line_id})

        payload = {
            "CurrentPage": 1,
            "PageSize": page_size,
            "FilterInfo": {
                "Logic": "And",
                "Filters": filters,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers(route))
            resp.raise_for_status()
            return resp.json()

    async def fetch_defect_summary(
        self,
        start_date: str,
        end_date: str,
        line_id: Optional[int] = None,
        deduplicate: bool = True,
        page_size: int = 5000,
    ) -> dict[str, Any]:
        """
        Query DefectData Report (POST /api/app/report/787763718877829/data).
        Returns defect records. When deduplicate=True (Type="0"), returns 1 row per unique bad lot.
        """
        url = f"{self.base_url}/api/app/report/787763718877829/data"
        route = "/RPT-ReportManagement/QualityReport/DefectData"

        filters = [
            {"Field": "StartDate", "Operator": "Equal", "Value": start_date},
            {"Field": "EndDate", "Operator": "Equal", "Value": end_date},
            {"Field": "Type", "Operator": "Equal", "Value": "0" if deduplicate else "1"},
        ]
        if line_id is not None:
            # Preserve literal typo in Jinchen API: 'ProdectionLine'
            filters.append({"Field": "ProdectionLine", "Operator": "Equal", "Value": line_id})

        payload = {
            "CurrentPage": 1,
            "PageSize": page_size,
            "FilterInfo": {
                "Logic": "And",
                "Filters": filters,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._get_headers(route))
            resp.raise_for_status()
            return resp.json()

    async def get_normalized_data(
        self,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[MESProductionRecord]:
        """
        Fetch and normalize real Jinchen MES data into MESProductionRecord models
        for the deterministic BusinessMetricEngine.
        """
        target_date = date_from or datetime.now().date()
        target_shift = (shift or "A").upper()

        start_str, end_str = self._get_shift_window(target_date, target_shift)
        line_id = self._resolve_line_id(line)

        try:
            prod_data = await self.fetch_production_summary(start_str, end_str, line_id)
            defect_data = await self.fetch_defect_summary(start_str, end_str, line_id, deduplicate=True)

            prod_items = prod_data.get("Items", [])
            total_produced = prod_data.get("TotalCount", len(prod_items))
            total_bad = defect_data.get("TotalCount", len(defect_data.get("Items", [])))

            # If no data returned from live system, return empty list
            if total_produced == 0 and total_bad == 0:
                return []

            # Determine normalized line string
            line_str = line.upper() if line else "ALL"
            if line_str not in ("KM1", "KM2", "KM3") and line_id:
                line_str = JINCHEN_LINE_REVERSE.get(line_id, line_str)

            # Construct normalized record
            # In solar manufacturing:
            # getin_quantity: candidate initial station input (total produced + total bad)
            # departure_quantity: completed output from final stages
            # bad_quantity: deduplicated defective modules
            # scrap_quantity: modules classified as Grade Z / Scrap
            scrap_count = 0
            for item in prod_items:
                if item.get("MinGrade") in ("Z", "Scrap", "SCRAP"):
                    scrap_count += 1

            record = MESProductionRecord(
                record_date=target_date,
                line=line_str,
                shift=target_shift,
                area="Final Process",
                getin_quantity=total_produced,
                departure_quantity=total_produced,
                bad_quantity=total_bad,
                scrap_quantity=scrap_count,
                workorder=prod_items[0].get("WorkOrderCode") if prod_items else None,
            )
            return [record]

        except Exception as e:
            logger.error(f"Failed to fetch and normalize Jinchen MES data: {e}")
            raise


def get_adapter(adapter_type: str) -> MESAdapterBase:
    """
    Factory function: returns the appropriate MES adapter.

    Args:
        adapter_type: 'mock' or 'jinchen'
                      Configured via MES_ADAPTER environment variable.
    """
    if adapter_type == "mock":
        from app.adapters.mock_adapter import MockMESAdapter
        return MockMESAdapter()
    elif adapter_type == "jinchen":
        return JinchenMESAdapter()
    else:
        raise ValueError(
            f"Unknown adapter type: '{adapter_type}'. "
            f"Valid values: 'mock', 'jinchen'."
        )
