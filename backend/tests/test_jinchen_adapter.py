import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import patch, MagicMock

from app.adapters.jinchen_adapter import (
    JinchenMESAdapter,
    JINCHEN_LINE_IDS,
    JINCHEN_LINE_REVERSE,
    get_adapter,
)
from app.models.mes import MESProductionRecord


def test_jinchen_adapter_factory():
    adapter = get_adapter("jinchen")
    assert isinstance(adapter, JinchenMESAdapter)
    assert adapter.ADAPTER_NAME == "JinchenMESAdapter"


def test_jinchen_line_id_resolution():
    adapter = JinchenMESAdapter()
    assert adapter._resolve_line_id("KM1") == 738616585908229
    assert adapter._resolve_line_id("RenK-1") == 738616585908229
    assert adapter._resolve_line_id("KM2") == 738620881702917
    assert adapter._resolve_line_id("RenK-2") == 738620881702917
    assert adapter._resolve_line_id("Line 3") == 738620932063237
    assert adapter._resolve_line_id("Line 4") == 764804556390405
    assert adapter._resolve_line_id(None) is None


def test_jinchen_shift_window():
    adapter = JinchenMESAdapter()
    ref_date = date(2026, 10, 3)

    # Shift A: 07:00 to 15:00
    start_a, end_a = adapter._get_shift_window(ref_date, "A")
    assert start_a == "2026-10-03 07:00:00"
    assert end_a == "2026-10-03 15:00:00"

    # Shift B: 15:00 to 23:00
    start_b, end_b = adapter._get_shift_window(ref_date, "B")
    assert start_b == "2026-10-03 15:00:00"
    assert end_b == "2026-10-03 23:00:00"

    # Shift C: 23:00 to 07:00 next day
    start_c, end_c = adapter._get_shift_window(ref_date, "C")
    assert start_c == "2026-10-03 23:00:00"
    assert end_c == "2026-10-04 07:00:00"


def test_jinchen_headers():
    adapter = JinchenMESAdapter(
        base_url="http://10.69.12.10:8000",
        api_token="test_jwt_token_123",
    )
    headers = adapter._get_headers("/test/route")
    assert headers["Authorization"] == "Bearer test_jwt_token_123"
    assert headers["X-Requested-With"] == "XMLHttpRequest"
    assert headers["X-Button-Permission"] == "Search"
    assert headers["Route"] == "/test/route"
    assert headers["Origin"] == "http://10.69.12.10:8000"


def test_jinchen_capability():
    adapter = JinchenMESAdapter()
    cap = adapter.get_capability()
    assert not cap.is_mock
    assert cap.schema_confirmed
    assert cap.engine_confirmed
    assert "10.69.12.10:8000" in cap.notes[1]


@pytest.mark.asyncio
async def test_jinchen_get_normalized_data_mocked():
    adapter = JinchenMESAdapter()

    mock_prod_response = {
        "TotalCount": 1027,
        "Items": [
            {
                "No": 1,
                "LotNumber": "R1400040260103133",
                "WorkOrderCode": "0000012311",
                "FinalProductionLineCode": "RenK-2",
                "FinalProcess": "Packing",
                "MinGrade": "A1",
            },
            {
                "No": 2,
                "LotNumber": "R5300040261968463",
                "WorkOrderCode": "0000012238",
                "FinalProductionLineCode": "RenK-2",
                "FinalProcess": "Framing",
                "MinGrade": "Z",  # Scrap
            },
        ],
    }

    mock_defect_response = {
        "TotalCount": 42,
        "Items": [
            {"LotNumber": "R1400040260103133", "DefectCode": "EL08"}
        ],
    }

    with patch.object(adapter, "fetch_production_summary", return_value=mock_prod_response), \
         patch.object(adapter, "fetch_defect_summary", return_value=mock_defect_response):

        records = await adapter.get_normalized_data(
            line="KM2",
            shift="A",
            date_from=date(2026, 10, 3),
        )

        assert len(records) == 1
        rec = records[0]
        assert isinstance(rec, MESProductionRecord)
        assert rec.line == "KM2"
        assert rec.shift == "A"
        assert rec.departure_quantity == 1027
        assert rec.bad_quantity == 42
        assert rec.scrap_quantity == 1
        assert rec.workorder == "0000012311"
