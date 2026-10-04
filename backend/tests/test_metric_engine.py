import json
from pathlib import Path
from datetime import datetime
import pytest

from app.models.mes import MESProductionRecord
from app.services.metric_engine import metric_engine

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "business_metrics"

def load_golden_data():
    with open(FIXTURE_DIR / "golden_metrics.json") as f:
        return json.load(f)

@pytest.mark.parametrize("scenario", load_golden_data())
def test_golden_metrics(scenario):
    # Parse records
    records = []
    for r in scenario["records"]:
        record = MESProductionRecord(
            record_date=datetime.strptime(r["record_date"], "%Y-%m-%d").date(),
            line=r["line"],
            shift=r["shift"],
            area=r["area"],
            getin_quantity=r["getin_quantity"],
            departure_quantity=r["departure_quantity"],
            bad_quantity=r["bad_quantity"],
            scrap_quantity=r.get("scrap_quantity", 0)
        )
        records.append(record)
    
    # Verify expectations
    expected = scenario["expected"]
    for metric_name, expected_val in expected.items():
        result = metric_engine.calculate(metric_name, records)
        
        if isinstance(expected_val, str) and expected_val in ("zero_denominator", "missing_data"):
            assert result.status == expected_val
        else:
            assert result.status == "success"
            assert result.value == expected_val

def test_undefined_metrics_handled_gracefully():
    records = [
        MESProductionRecord(
            record_date=datetime.now().date(),
            line="KM1",
            shift="A",
            area="Assembly",
            getin_quantity=100,
            departure_quantity=90,
            bad_quantity=10,
            scrap_quantity=0
        )
    ]
    undefined_metrics = ["oee", "wip", "process_loss", "first_pass_yield", "rework_rate", "cycle_time", "downtime"]
    
    for metric in undefined_metrics:
        result = metric_engine.calculate(metric, records)
        assert result.status == "definition_required"
        assert result.value is None

def test_missing_metric_name():
    result = metric_engine.calculate("", [])
    assert result.status == "missing_data"

def test_unsupported_metric():
    records = [
        MESProductionRecord(
            record_date=datetime.now().date(),
            line="KM1",
            shift="A",
            area="Assembly",
            getin_quantity=100,
            departure_quantity=90,
            bad_quantity=10,
            scrap_quantity=0
        )
    ]
    result = metric_engine.calculate("some_made_up_metric", records)
    assert result.status == "unsupported"
    assert result.value is None
