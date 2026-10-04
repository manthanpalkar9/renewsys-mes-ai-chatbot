"""
Business Metric Engine.

Calculates manufacturing KPIs deterministically from normalized MES data.
The LLM is explicitly forbidden from performing these calculations.
Definitions match the Phase 1 SRS exactly.
"""

from typing import List, Optional
from app.models.mes import MESProductionRecord, MetricResult


class BusinessMetricEngine:
    
    def calculate(self, metric_name: str, records: List[MESProductionRecord]) -> MetricResult:
        """Calculate a requested metric from a list of normalized production records."""
        if not metric_name:
            return MetricResult(
                metric_name="unknown",
                status="missing_data",
                message="No metric name provided."
            )

        kpi_lower = metric_name.lower().replace(" ", "_").replace("-", "_")
        
        # Aggregate totals
        total_getin = sum(r.getin_quantity for r in records) if records else 0
        total_departures = sum(r.departure_quantity for r in records) if records else 0
        total_bad = sum(r.bad_quantity for r in records) if records else 0
        total_scrap = sum(r.scrap_quantity for r in records) if records else 0

        # Undefined metrics (SRS D10, D11, D12, 14.2)
        undefined_metrics = {
            "oee": "OEE requires Availability x Performance x Quality. Downtime and Cycle time sources are unconfirmed.",
            "wip": "WIP depends on unresolved quantity semantics (D10).",
            "process_loss": "Process loss definition unknown (D11). Cannot calculate.",
            "first_pass_yield": "First Pass Yield depends on rework loop definition (D12).",
            "rework_rate": "Rework rate depends on rework loop definition (D12).",
            "cycle_time": "Cycle time source not confirmed (process timestamps TBD).",
            "downtime": "Downtime source not confirmed (downtime event log existence TBD)."
        }
        
        if kpi_lower in undefined_metrics:
            return MetricResult(
                metric_name=metric_name,
                status="definition_required",
                message=undefined_metrics[kpi_lower],
                formula_note="NOT PROPOSED - pending business definition"
            )

        if not records:
            return MetricResult(
                metric_name=metric_name,
                status="missing_data",
                message="No data available for the requested period/filters."
            )

        # Defined metrics
        if kpi_lower in ("total_production", "production", "get_in_quantity", "getin"):
            return MetricResult(
                metric_name=metric_name,
                value=float(total_getin),
                unit="modules",
                formula_note="DEFINED - Supported by SRS"
            )
        elif kpi_lower in ("departure_quantity", "departures", "throughput"):
            return MetricResult(
                metric_name=metric_name,
                value=float(total_departures),
                unit="modules",
                formula_note="DEFINED - Supported by SRS"
            )
        elif kpi_lower in ("bad_quantity", "bad"):
            return MetricResult(
                metric_name=metric_name,
                value=float(total_bad),
                unit="modules",
                formula_note="DEFINED - Supported by SRS"
            )
        elif kpi_lower in ("scrap_quantity", "scrap"):
            return MetricResult(
                metric_name=metric_name,
                value=float(total_scrap),
                unit="modules",
                formula_note="DEFINED - Supported by SRS"
            )
        elif kpi_lower == "yield":
            if total_getin == 0:
                return MetricResult(metric_name=metric_name, status="zero_denominator", message="Total production is zero, cannot calculate yield.")
            val = round(((total_getin - total_bad) / total_getin) * 100, 2)
            return MetricResult(metric_name=metric_name, value=val, unit="%", formula_note="DEFINED - Supported by SRS")
        elif kpi_lower in ("defect_rate", "defect rate"):
            if total_getin == 0:
                return MetricResult(metric_name=metric_name, status="zero_denominator", message="Total production is zero, cannot calculate defect rate.")
            val = round((total_bad / total_getin) * 100, 2)
            return MetricResult(metric_name=metric_name, value=val, unit="%", formula_note="DEFINED - Supported by SRS")
        elif kpi_lower in ("scrap_rate", "scrap rate"):
            if total_getin == 0:
                return MetricResult(metric_name=metric_name, status="zero_denominator", message="Total production is zero, cannot calculate scrap rate.")
            val = round((total_scrap / total_getin) * 100, 2)
            return MetricResult(metric_name=metric_name, value=val, unit="%", formula_note="DEFINED - Supported by SRS")
        
        return MetricResult(
            metric_name=metric_name,
            status="unsupported",
            message=f"Metric '{metric_name}' is not recognized or supported."
        )

metric_engine = BusinessMetricEngine()
