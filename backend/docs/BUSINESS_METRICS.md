# Business Metrics Definition

This document serves as the authoritative source for business metrics calculated by the Renewsys MES AI Chatbot (Phase 2.5).

All definitions are sourced directly from the project SRS (`Renewsys_MES_AI_Chatbot_Phase1_SRS_v3_Final.pdf`). The LLM does **not** calculate these metrics; they are calculated deterministically by the Business Metric Engine using these formulas.

## Defined Metrics

| Metric | Business Definition | Formula | Required Input Fields | Units | Status |
|--------|---------------------|---------|-----------------------|-------|--------|
| **Total Production** | Total modules entering the process line (sum of get-in events) | `SUM(getin_quantity)` | `getin_quantity` | modules | PROPOSED |
| **Get-in Quantity** | Same as Total Production | `SUM(getin_quantity)` | `getin_quantity` | modules | PROPOSED |
| **Departure Quantity** | Total modules successfully leaving the process line | `SUM(departure_quantity)` | `departure_quantity` | modules | PROPOSED |
| **Bad Quantity** | Total modules flagged with a defect | `SUM(bad_quantity)` | `bad_quantity` | modules | PROPOSED |
| **Scrap Quantity** | Total modules flagged as scrapped/damaged | `SUM(scrap_quantity)` | `scrap_quantity` | modules | PROPOSED |
| **Yield** | Percentage of good modules relative to total modules | `(Total Production - Bad Quantity) / Total Production * 100` | `getin_quantity`, `bad_quantity` | % | PROPOSED |
| **Defect Rate** | Percentage of defective modules | `(Bad Quantity / Total Production) * 100` | `getin_quantity`, `bad_quantity` | % | PROPOSED |
| **Scrap Rate** | Percentage of scrapped modules | `(Scrap Quantity / Total Production) * 100` | `getin_quantity`, `scrap_quantity` | % | PROPOSED |
| **Throughput** | Modules departing the line | `SUM(departure_quantity)` | `departure_quantity` | modules | PROPOSED |

## Undefined / Pending Metrics

The following metrics are explicitly marked as **DEFINITION REQUIRED** because they depend on unresolved business rules in the SRS. The engine will safely return a `definition_required` status rather than guessing a formula.

| Metric | Pending Rule | SRS Section | Engine Behavior |
|--------|--------------|-------------|-----------------|
| **OEE** | Depends on confirmed downtime event logs and cycle time source. | 14.2 | Returns `definition_required` |
| **WIP** | Depends on unresolved D10 (Quantity/WIP semantics). | D10, 14.2 | Returns `definition_required` |
| **Process Loss** | Depends on unresolved D11 (Process loss calculation method). | D11, 14.2 | Returns `definition_required` |
| **First Pass Yield** | Depends on unresolved D12 (Rework loops). | D12, 14.2 | Returns `definition_required` |
| **Rework Rate** | Depends on unresolved D12 (Rework loops). | D12, 14.2 | Returns `definition_required` |
| **Cycle Time** | Depends on unconfirmed process timestamp data. | 14.2 | Returns `definition_required` |
| **Downtime** | Depends on unconfirmed downtime event log data. | 14.2 | Returns `definition_required` |

## Arithmetic Rules & Edge Cases

1. **Zero Denominator:** If `Total Production` is 0, any division (e.g., Yield, Defect Rate, Scrap Rate) must return `null` or a safe status, not `Infinity` or `NaN`.
2. **Missing Data:** If required fields are entirely missing from a dataset, the metric must return `null` and a controlled message.
3. **Rounding:** Percentage metrics (Yield, Defect Rate, Scrap Rate) are rounded to exactly 2 decimal places. Counts are integers.
