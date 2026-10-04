"""
Jinchen MES Adapter

╔══════════════════════════════════════════════════════════════════════════════╗
║  NOT YET IMPLEMENTABLE - PENDING SCHEMA DISCOVERY                          ║
║                                                                              ║
║  This adapter is a placeholder only. It CANNOT be completed until:          ║
║    1. The actual Jinchen MES database engine is confirmed (B1: AMBIGUOUS)   ║
║    2. The actual schema is obtained from IT/DBA (C1: CONFIRMED action)      ║
║    3. Network connectivity is verified (OI-04: Open Issue, Section 35)      ║
║    4. Read-only account credentials are provisioned (F6: CONFIRMED)         ║
║    5. Business definitions are validated (D10-D13: IDK/TBD)                 ║
║                                                                              ║
║  Stakeholder-provided connection info (REQUIRES TECHNICAL VERIFICATION):    ║
║    Host: 10.69.12.20 (B2: STAKEHOLDER-PROVIDED)                             ║
║    Port: 8000 (B3: STAKEHOLDER-PROVIDED)                                    ║
║    Database: Jinchen MES (B4: STAKEHOLDER-PROVIDED)                         ║
║    Auth: SQL and AD available (B5: STAKEHOLDER-PROVIDED)                    ║
║                                                                              ║
║  Open Issues (Section 35):                                                  ║
║    OI-01: Actual DB engine (B1)                                             ║
║    OI-02: Actual schema (C1)                                                ║
║    OI-03: Network path (B6 vs G1/G2) - 'MES server is in China'            ║
║    OI-04: Reachability of 10.69.12.20                                       ║
║    OI-07: DB auth mechanism for the application account                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

SRS References:
  - B1 (AMBIGUOUS): Database technology 'Over to you'
  - B2 (STAKEHOLDER-PROVIDED - REQUIRES VERIFICATION): Host 10.69.12.20
  - B3 (STAKEHOLDER-PROVIDED - REQUIRES VERIFICATION): Port 8000
  - B6 (STAKEHOLDER-PROVIDED - REQUIRES VERIFICATION): 'MES server is in China'
  - C1 (CONFIRMED): Schema must be requested from IT/DBA
  - F2 (CONFIRMED): SELECT-only
  - F6 (CONFIRMED): Dedicated read-only account
  - Section 12.3: Adapter-based DB access (PROPOSED TECHNICAL SOLUTION)
"""

from typing import Optional
from app.adapters.base import MESAdapterBase, QueryResult, AdapterCapability


class JinchenMESAdapter(MESAdapterBase):
    """
    Placeholder for the real Jinchen MES adapter.

    STATUS: NOT YET IMPLEMENTABLE

    This class will be completed once:
    - IT/DBA confirms the database engine (B1: currently AMBIGUOUS)
    - Authorized schema discovery is completed (C1: CONFIRMED action required)
    - Network connectivity to 10.69.12.20:8000 is verified (OI-04)
    - Read-only credentials are provisioned (F6: CONFIRMED requirement)
    - Business definitions D10-D13 are resolved (all IDK/TBD)

    Until then, use MockMESAdapter for all development work.
    """

    NOT_READY_MESSAGE = (
        "JinchenMESAdapter is not yet implementable. "
        "Pending: DB engine confirmation (B1), schema discovery (C1), "
        "network verification (OI-04). Use MES_ADAPTER=mock for development."
    )

    async def execute_query(
        self,
        sql: str,
        params: Optional[dict] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        raise NotImplementedError(self.NOT_READY_MESSAGE)

    async def test_connection(self) -> bool:
        raise NotImplementedError(self.NOT_READY_MESSAGE)

    def get_capability(self) -> AdapterCapability:
        return AdapterCapability(
            adapter_name="JinchenMESAdapter",
            is_mock=False,
            schema_confirmed=False,
            engine_confirmed=False,
            notes=[
                "STATUS: NOT YET IMPLEMENTABLE",
                "Awaiting: DB engine (B1: AMBIGUOUS)",
                "Awaiting: Schema from IT/DBA (C1: CONFIRMED action required)",
                "Awaiting: Network verification (OI-04: Open Issue)",
                "Awaiting: Read-only credentials (F6: CONFIRMED requirement)",
                "Awaiting: Business definitions D10-D13 (all TBD/IDK)",
                "Stakeholder DB info: host=10.69.12.20 port=8000 (REQUIRES VERIFICATION)",
            ],
        )

    async def get_mock_schema_info(self) -> dict:
        return {
            "status": "NOT_AVAILABLE",
            "reason": self.NOT_READY_MESSAGE,
        }

    async def get_normalized_data(
        self,
        line: Optional[str] = None,
        shift: Optional[str] = None,
        date_from: Optional[any] = None,
        date_to: Optional[any] = None,
    ) -> list[any]:
        raise NotImplementedError(self.NOT_READY_MESSAGE)


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
            f"Valid values: 'mock', 'jinchen'. "
            f"Real adapter not implementable until schema confirmed (C1, B1)."
        )
