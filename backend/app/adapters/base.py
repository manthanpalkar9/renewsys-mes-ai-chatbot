"""
MES Adapter Abstract Base

SRS Reference:
  - Section 23.2 (PROPOSED TECHNICAL SOLUTION): MESRepository abstraction
  - B1 (AMBIGUOUS): Database engine unknown -> adapter pattern required
  - F2 (CONFIRMED): SELECT-only operations
  - F6 (CONFIRMED): Dedicated read-only database account
  - Section 24 (PROPOSED): Two-track delivery

The adapter pattern ensures:
  1. Development can proceed with MockMESAdapter without knowing the real schema.
  2. The real JinchenMESAdapter can be plugged in once schema is confirmed.
  3. No MES schema details are invented.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import date


@dataclass
class QueryResult:
    """Standard result object returned by all adapter queries."""
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    query_time_ms: float = 0.0
    # I4 (CONFIRMED): data freshness
    data_freshness_note: str = "~24-hour data freshness (L1: CONFIRMED)"
    adapter_note: str = ""
    # FR-CORE-010 (CONFIRMED): distinguish measured vs calculated
    is_calculated: bool = False


@dataclass
class AdapterCapability:
    """What this adapter can/cannot do - for transparent capability reporting."""
    adapter_name: str
    is_mock: bool
    schema_confirmed: bool = False
    engine_confirmed: bool = False
    notes: list[str] = field(default_factory=list)


class MESAdapterBase(ABC):
    """
    Abstract base for all MES data adapters.

    Subclasses:
      MockMESAdapter      - development/testing with conceptual mock data
      JinchenMESAdapter   - real Jinchen MES (not completable until schema confirmed)

    CRITICAL: Phase 1 is read-only. Only SELECT operations are permitted.
    INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE are NEVER allowed.
    See: F1, F2, F3 (CONFIRMED), Section 13.3
    """

    READ_ONLY_VIOLATION_MSG = (
        "Write operation attempted. Phase 1 is read-only (F2: CONFIRMED). "
        "Operation blocked."
    )

    @abstractmethod
    async def execute_query(
        self,
        sql: str,
        params: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """
        Execute a validated, SELECT-only query.
        The adapter must enforce read-only at this layer as a defense-in-depth measure.
        Database-level enforcement via read-only account is the primary control (F6).
        """
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the MES database is reachable."""
        ...

    @abstractmethod
    def get_capability(self) -> AdapterCapability:
        """Return capability/status information for this adapter."""
        ...

    @abstractmethod
    async def get_mock_schema_info(self) -> dict:
        """
        Return the schema context used for query generation.
        For mock: returns the conceptual mock schema.
        For real: returns discovered schema (once available).
        """
        ...

    def _validate_read_only(self, sql: str) -> None:
        """
        Enforce SELECT-only at the application layer.
        This is a PROPOSED TECHNICAL SAFETY CONTROL (Section 13.3) in addition
        to the confirmed database-level read-only account (F6: CONFIRMED).

        Blocks: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE
        """
        forbidden = [
            "insert", "update", "delete", "drop", "alter",
            "truncate", "create", "grant", "revoke", "exec",
            "execute", "xp_", "sp_",
        ]
        sql_lower = sql.lower().strip()
        for keyword in forbidden:
            # Check for keyword as a whole word at statement start or after semicolon
            import re
            if re.search(rf'(?:^|;)\s*{re.escape(keyword)}\b', sql_lower):
                raise PermissionError(
                    f"{self.READ_ONLY_VIOLATION_MSG} Keyword '{keyword.upper()}' "
                    f"detected and blocked."
                )

    @abstractmethod
    async def get_normalized_data(
        self,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Any]:
        """
        Fetch normalized MES data for the metric engine.
        Returns a list of MESProductionRecord.
        """
        ...
