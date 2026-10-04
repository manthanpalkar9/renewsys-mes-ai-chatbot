# Jinchen MES Field Mapping

This document provides the field mapping between the discovered Jinchen MES API interfaces and the internal normalized model (`MESProductionRecord`) utilized by the Renewsys Chatbot's deterministic `BusinessMetricEngine`.

---

## 1. Normalized Application Model (`MESProductionRecord`)

The application engine consumes data strictly via this normalized schema:

```python
class MESProductionRecord(BaseModel):
    record_date: date
    line: str
    shift: str
    area: str
    getin_quantity: int
    departure_quantity: int
    bad_quantity: int
    scrap_quantity: int
    workorder: Optional[str] = None
```

> **MODEL INTEGRITY RULE:**
> The normalized model remains **UNTOUCHED**. If a discovered Jinchen field has no current counterpart, it is designated as:
> `TBD — adapter mapping decision required`.

---

## 2. DefectData UI Filter → API Request Mapping

The Jinchen DefectData UI (`POST /api/app/report/787763718877829/data`) exposes exactly nine (9) request-side filters.

| Jinchen UI Field | API Field Name | Operator | Value Type | Normalized MES Field | Evidence | Confidence |
|---|---|---|---|---|---|---|
| **StartDate** | `StartDate` | `Equal` | DateTime String (`YYYY-MM-DD HH:mm:ss`) | Filters `record_date` lower bound | Directly observed in request payload | **CONFIRMED** |
| **EndDate** | `EndDate` | `Equal` | DateTime String (`YYYY-MM-DD HH:mm:ss`) | Filters `record_date` upper bound | Directly observed in request payload | **CONFIRMED** |
| **OrderNumber** | `OrderNumber` | `Equal` | Numeric ID (`Int64`) | Maps to `workorder` (internal ID) | Directly observed in request payload | **CONFIRMED** |
| **ReasonCode** | `ReasonCode` | `Equal` | String (e.g. `"EL08"`) | *TBD — adapter mapping decision required* (Defect breakdown) | Directly observed in request payload | **CONFIRMED** |
| **ProcessesId** | `ProcessesId` | `Equal` | Numeric ID (`Int64`) | Maps to `area` (internal ID) | Directly observed in request payload | **CONFIRMED** |
| **Grade** | `Grade` | `Equal` | String (e.g. `"A2"`) | *TBD — adapter mapping decision required* (Quality classification) | Directly observed in request payload | **CONFIRMED** |
| **Production Line** | `ProdectionLine` | `Equal` | Numeric ID (`Int64`) | Maps to `line` (e.g. RenK-2 ID `738620881702917`) | Directly observed in request payload (**preserve literal typo**) | **CONFIRMED** |
| **ExcludeDublicate** | `Type` | `Equal` | String (`"0"` or `"1"`) | Determines `bad_quantity` aggregation (Yes="0", No="1") | Controlled payload and response test | **CONFIRMED** |
| **LotNumbers** | `LotNumbers` | `Contains` | String (e.g. `"R5300040261968210"`) | Individual module trace | Directly observed in request payload | **CONFIRMED** |

---

## 3. DefectData Response Fields → Normalized Model Mapping

Endpoint: `POST http://10.69.12.10:8000/api/app/report/787763718877829/data`

| Jinchen Response Field | Field Type | Target Normalized Field | Mapping Logic & Evidence | Confidence |
|---|---|---|---|---|
| `LotNumber` | String | *TBD — adapter mapping decision required* | Unique module identifier. When `Type="0"`, COUNT(LotNumber) = distinct defective modules. | **CONFIRMED** (Field observed) / **INFERRED** (Deduplication logic) |
| `WorkOrderCode` | String | `workorder` | Direct string assignment. | **CONFIRMED** |
| `MaterialCode` | String | *TBD — adapter mapping decision required* | Product BOM code. | **CONFIRMED** |
| `TechnologyName` | String | *TBD — adapter mapping decision required* | Process stage group name. | **CONFIRMED** |
| `TechnologyStepName` | String | `area` | Process location/station name (e.g., Lamination, Testing). | **INFERRED** |
| `ProductionLineCode` | String | `line` | Direct code match (e.g., `"RenK-2"`, `"KM1"`, etc.). | **CONFIRMED** |
| `Laminator` | String | *TBD — adapter mapping decision required* | Machine equipment identifier. | **CONFIRMED** |
| `Layup` | String | *TBD — adapter mapping decision required* | Machine equipment identifier. | **CONFIRMED** |
| `Grade` | String | *TBD — adapter mapping decision required* | Output grade classification. | **CONFIRMED** |
| `DefectCode` | String | *TBD — adapter mapping decision required* | Defect category code (e.g., `"EL08"`). | **CONFIRMED** |
| `DefectDescription` | String | *TBD — adapter mapping decision required* | Human-readable defect reason. | **CONFIRMED** |
| `DefectPosition` | String | *TBD — adapter mapping decision required* | Physical module coordinate. | **CONFIRMED** |
| `ShiftName` | String | `shift` | Output shift name. **Response-only**; cannot be passed in request filter. | **CONFIRMED** |
| `CreationTime` | DateTime String | `record_date` | Timestamp defect was logged. | **CONFIRMED** |
| `UserName` | String | *TBD — adapter mapping decision required* | Operator login ID. | **CONFIRMED** |
| `TotalCount` | Integer | *TBD — adapter mapping decision required* | Total records returned by paginated query. | **CONFIRMED** |

---

## 4. Production API Response Fields → Normalized Model Mapping

Endpoint: `POST http://10.69.12.10:8000/api/app/lot/lots`

| Jinchen Lot Field | Field Type | Target Normalized Field | Mapping Logic & Evidence | Confidence |
|---|---|---|---|---|
| `LotNumber` | String | *TBD — adapter mapping decision required* | Module serial number. | **CONFIRMED** |
| `ProductionLineCode` | String | `line` | Matches normalized line (KM1, KM2, KM3, RenK-2). | **CONFIRMED** |
| `WorkOrderCode` | String | `workorder` | Work order identifier. | **CONFIRMED** |
| `TechnologyStepName` | String | `area` | Manufacturing area / step. | **INFERRED** |
| `QuantityInitial` | Float / Int | `getin_quantity` | Quantity entering station. Candidate for get-in metrics. | **INFERRED** (Requires business validation) |
| `Quantity` | Float / Int | `departure_quantity` | Current active quantity. Candidate for departure metrics. | **INFERRED** (Requires business validation) |
| `TrackInTime` | DateTime String | *Candidate `record_date`* | Timestamp module entered station. | **CONFIRMED** (Field observed) |
| `TrackOutTime` | DateTime String | *Candidate `record_date`* | Timestamp module exited station. Candidate for production timestamp. | **CONFIRMED** (Field observed) |
| `LastModificationTime` | DateTime String | *Candidate `record_date`* | Filtered by UI, but unconfirmed if equal to production date. | **TBD — requires confirmation from Jinchen/IT/DBA** |
| `StateFlag` / `StateFlagCode` | String / Int | *Production Filter* | States observed: "Finished", "Waiting for Track In", "Waiting for Track Out". | **CONFIRMED** (Field observed) / **TBD** (Valid production states) |
| `ScrapFlag` | Boolean / Int | `scrap_quantity` | Flag indicating scrapped module. | **INFERRED** (Requires validation) |
| `ReworkFlag` / `RepairFlag` | Boolean / Int | *TBD (D12 Rework)* | Flag indicating rework loop. | **INFERRED** (Pending D12 definition) |
| `HoldFlag` | Boolean / Int | *TBD — adapter mapping decision required* | Quality hold indicator. | **CONFIRMED** (Field observed) |
| `PackagedFlag` | Boolean / Int | *TBD — adapter mapping decision required* | Packaging stage indicator. | **CONFIRMED** (Field observed) |
| `Grade` | String | *TBD — adapter mapping decision required* | Module quality grade. | **CONFIRMED** (Field observed) |

---

## 5. Shift Schedule & Request Translation Rules

### Shift Schedule (CONFIRMED)
- **A (Morning):** `07:00 – 15:00`
- **B (Second):** `15:00 – 23:00`
- **C (Night):** `23:00 – 07:00` (crosses midnight into `D+1`)

### DefectData Shift Translation Rule (CONFIRMED Constraint)
- The DefectData API does **not** accept a shift filter parameter.
- The adapter must calculate the exact timestamp window from the requested calendar date and shift code, passing the values into `StartDate` and `EndDate`:
  - E.g. Shift A on `2026-09-28`: `StartDate = "2026-09-28 07:00:00"`, `EndDate = "2026-09-28 15:00:00"`.
  - E.g. Shift C on `2026-09-28`: `StartDate = "2026-09-28 23:00:00"`, `EndDate = "2026-09-29 07:00:00"`.
- If a query covers an entire calendar day, client-side filtering on response field `ShiftName` can optionally partition records.

---

## 6. Timezone Rules

- **Internal Chatbot Service:** Resolves user expressions (e.g. "today", "yesterday") in local system time.
- **Jinchen MES Timezone:** **TBD — requires confirmation from Jinchen/IT/DBA**.
- **Conversion Obligation:** If Jinchen timestamps are in China Standard Time (UTC+8) while Renewsys operates in Indian Standard Time (UTC+5:30), the adapter must perform explicit timezone translation when constructing `StartDate`/`EndDate` bounds and when parsing response timestamps.

---

## 7. Open Business Definitions (SRS Unresolved Items)

| Metric | Open SRS Issue | Status & Impact |
|---|---|---|
| **Total Production** | Lot state qualification | **TBD — requires confirmation from Jinchen/IT/DBA** on which `StateFlag` values constitute counted production. |
| **Bad Quantity** | Multi-defect deduplication | **CANDIDATE / STRONG EVIDENCE** that `Type="0"` gives 1 row per unique lot. Business sign-off required. |
| **WIP (D10)** | Quantity semantics | **TBD — requires business definition**. Candidate: Lots with state "In Process" / "Waiting for Track Out". |
| **Process Loss (D11)** | Accounting method | **TBD — requires business definition**. |
| **Rework Rate (D12)** | Rework definition | **TBD — requires business definition**. Candidate field: `ReworkFlag` / `RepairFlag`. |
| **OEE / FPY** | Machine downtime & cycle time logs | **TBD — requires confirmation from Jinchen/IT/DBA** on machine event log availability. |
