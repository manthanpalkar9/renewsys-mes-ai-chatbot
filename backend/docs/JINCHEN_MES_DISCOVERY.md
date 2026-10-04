# Jinchen MES Technical Discovery

## Overview
This document summarizes the technical discovery findings for integrating the Renewsys MES AI Chatbot with the Jinchen MES data source.

The application architecture uses a normalized `MESProductionRecord` model and a `MockMESAdapter`. Phase 3 focuses on discovering the real Jinchen MES interface to eventually implement `JinchenMESAdapter`.

> **CRITICAL ARCHITECTURAL CONSTRAINTS:**
> - The chatbot intent, context, date handling, validation, metric engine, and security layers are **FROZEN**.
> - Do NOT implement `JinchenMESAdapter` during Phase 3.1.
> - Do NOT modify `StructuredIntent` or `BusinessMetricEngine`.
> - Do NOT invent undocumented fields, formulas, or business rules.
> - All discoveries must be classified strictly as **CONFIRMED**, **INFERRED**, or **TBD**.

---

## 1. Network Topology & Base URLs

### Stakeholder Specification vs. Observed Deployment
- **Stakeholder-Provided Host (Initial SRS B2/B3):** `10.69.12.20:8000` (Presumed `JinchenMES` database server, requires further verification/authorization).
- **Active Web UI & API Endpoint (Directly Observed):** `http://10.69.12.10:8000`
- **Frontend Version Observed:** `2026.7.8.3`
- **Backend Version Observed:** `2026.8.10.1`
- **Service Nature:** HTTP REST API and Web Management Portal (Port 8000 serves an ASP.NET / Web API backend, not a raw relational database port).
- **Access Rule (SRS F6):** The chatbot requires **read-only** querying. Write operations (INSERT, UPDATE, DELETE, lot release, status modifications) are strictly forbidden.

---

## 2. Phase 3.1 — API Discovery Results

### A. Production API
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/lot/lots`
- **Confidence:** **CONFIRMED** (Directly observed from API/UI)
- **Description:** Returns production lot records including lifecycle timestamps, process line identifiers, work orders, material codes, and status flags.

### B. DefectData API
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/report/787763718877829/data`
- **Confidence:** **CONFIRMED** (Directly observed from API/UI)
- **Description:** Report data endpoint returning defect events, failure descriptions, process locations, and quality grades.
- **Observed Request Structure:**
  ```json
  {
    "CurrentPage": 1,
    "FilterInfo": {
      "Logic": "And",
      "Filters": [
        {
          "Field": "StartDate",
          "Operator": "Equal",
          "Value": "2026-09-28 00:00:00"
        }
      ]
    },
    "PageSize": 20
  }
  ```
- **Filter Evaluation:** The report backend evaluates supplied filters strictly using `AND` logic (`"Logic": "And"`).

### C. DefectData Request Filter Mappings
The Jinchen DefectData UI exposes **exactly nine (9)** request filters. No other filters exist on this UI screen.

> **CRITICAL FILTER RULE:**
> Do **NOT** add `Shift`, `WorkOrder`, or `Material` as DefectData request filters unless independently verified by API reflection or schema audit. They are absent from the DefectData request filter specification.

| UI Filter Name | API Field Name | Operator | Value Type / Example | Evidence & Discovery Notes | Confidence |
|---|---|---|---|---|---|
| **StartDate** | `StartDate` | `Equal` | String (`YYYY-MM-DD HH:mm:ss`) | Directly observed in request payload | **CONFIRMED** |
| **EndDate** | `EndDate` | `Equal` | String (`YYYY-MM-DD HH:mm:ss`) | Directly observed in request payload | **CONFIRMED** |
| **OrderNumber** | `OrderNumber` | `Equal` | Numeric ID (`Int64`) | Internal work order ID in Jinchen | **CONFIRMED** |
| **ReasonCode** | `ReasonCode` | `Equal` | String (e.g. `"EL08"`) | Defect reason code | **CONFIRMED** |
| **ProcessesId** | `ProcessesId` | `Equal` | Numeric ID (`Int64`) | Internal manufacturing process ID | **CONFIRMED** |
| **Grade** | `Grade` | `Equal` | String (e.g. `"A2"`) | Quality grade classification | **CONFIRMED** |
| **Production Line** | `ProdectionLine` | `Equal` | Numeric ID (`Int64`) | **Preserve literal typo** `"ProdectionLine"`. Example: Line `RenK-2` maps to internal ID `738620881702917` | **CONFIRMED** |
| **ExcludeDublicate** | `Type` | `Equal` | String (`"0"` or `"1"`) | ExcludeDublicate = Yes maps to `Type = "0"`. ExcludeDublicate = No maps to `Type = "1"` | **CONFIRMED** |
| **LotNumbers** | `LotNumbers` | `Contains` | String (e.g. `"R5300040261968210"`) | Serial / Lot number search filter | **CONFIRMED** |

### D. DefectData Response Fields
Observed response records from `POST /api/app/report/787763718877829/data` contain the following fields:
- `LotNumber` (String): Unique identifier of the solar module/lot
- `WorkOrderCode` (String): Human-readable work order reference
- `MaterialCode` (String): Bill of materials item code
- `TechnologyName` (String): Process technology definition
- `TechnologyStepName` (String): Specific manufacturing station (e.g. Framing, Testing)
- `ProductionLineCode` (String): Line identifier (e.g. RenK-2)
- `Laminator` (String): Specific laminating machine identifier
- `Layup` (String): Layup station identifier
- `Grade` (String): Output grade (e.g. A, A2, B)
- `DefectCode` (String): Standardized defect symptom code (e.g. EL08)
- `DefectDescription` (String): Human-readable description of defect
- `DefectPosition` (String): Physical location/cell coordinate of defect
- `ShiftName` (String): Shift on which defect was logged (e.g. "Morning", "Second", "Night")
- `CreationTime` (DateTime String): Defect entry timestamp
- `UserName` (String): Operator who recorded the defect
- `TotalCount` (Integer): Total records matching the filter criteria

### E. Production Response Fields
Observed response records from `POST /api/app/lot/lots` contain:
- `LotNumber` (String): Unique module serial / lot identifier
- `OrgWorkOrderId` / `WorkOrderId` (Numeric IDs)
- `OrgWorkOrderCode` / `WorkOrderCode` (String)
- `MaterialId` (Numeric ID) / `MaterialCode` (String)
- `Grade` (String): Quality rating
- `ProductionLineId` (Numeric ID) / `ProductionLineCode` (String)
- `QuantityInitial` (Integer / Float): Starting quantity of the lot
- `Quantity` (Integer / Float): Current valid quantity
- `TechnologyName` (String) / `TechnologyStepName` (String)
- `StartWaitTime` (DateTime String)
- `StartProcessTime` (DateTime String)
- `TrackInTime` (DateTime String): Timestamp module entered station
- `TrackOutTime` (DateTime String): Timestamp module exited station
- `StateFlag` (String) / `StateFlagCode` (Integer): Current processing state
- `RepairFlag` (Boolean / Integer): Flag indicating rework/repair
- `ReworkFlag` (Boolean / Integer): Flag indicating rework loop
- `HoldFlag` (Boolean / Integer): Flag indicating quality hold
- `ScrapFlag` (Boolean / Integer): Flag indicating scrapped module
- `PackagedFlag` (Boolean / Integer): Flag indicating module packaging
- `CreationTime` (DateTime String): Creation timestamp
- `LastModificationTime` (DateTime String): Last update timestamp

### F. Shift Mapping & Timing
Discovered shift schedule from Jinchen Base configuration:
- **Shift A (Morning):** `07:00 – 15:00`
- **Shift B (Second):** `15:00 – 23:00`
- **Shift C (Night):** `23:00 – 07:00` (Crosses midnight into the subsequent calendar day)

> **CRITICAL SHIFT FILTER DISTINCTION:**
> `ShiftName` is observed as an output field in the DefectData response.
> There is **NO** request-side `Shift` parameter on the DefectData API request.
> To query defects for a specific shift, the adapter or application must construct exact `StartDate` and `EndDate` timestamps covering that shift's operational window, or filter records client-side using `ShiftName`.

---

## 3. Semantic Uncertainties & Analysis

### G. Production Semantic Uncertainties
1. **Query Date Boundary:**
   - In QueryLotReport UI, date filtering was observed binding to `LastModificationTime`.
   - `LastModificationTime` changes whenever any attribute or status is updated. It does **not** represent production completion or station entry.
   - **Status:** **TBD — Business confirmation required** before treating `LastModificationTime` as the production date.
2. **Lot State Granularity:**
   - Production lots exhibit multiple distinct states: `Finished`, `Waiting for Track In`, `Waiting for Track Out`, `In Process`, etc.
   - Counting all returned lots as "Total Production" would count incomplete or queued units.
   - **Rule:** Do **NOT** define Total Production as `COUNT(all returned lots)` unless explicitly confirmed by business stakeholders.

### H. Defect Semantic Uncertainties & ExcludeDublicate Analysis
1. **Multiple Defect Records per Lot:**
   - A single solar module lot (`LotNumber`) can trigger multiple defect rows if it has multiple defect codes or defects at multiple positions.
   - Therefore, `COUNT(defect records)` is **NOT** equal to `bad_quantity` (defective modules count).
2. **ExcludeDublicate Controlled Trial:**
   - With `ExcludeDublicate = No` (`Type = "1"`): **548 records** representing **329 unique lots**.
   - With `ExcludeDublicate = Yes` (`Type = "0"`): **329 records** representing **329 unique lots**.
   - **Inference:** Setting `Type = "0"` (`ExcludeDublicate = Yes`) deduplicates by `LotNumber`, yielding exactly one defect record per affected module lot.
   - **Status:** **CANDIDATE / STRONG EVIDENCE — BUSINESS CONFIRMATION REQUIRED**. Do not formally equate `bad_quantity = COUNT(DISTINCT LotNumber)` without written business sign-off.

---

## 4. Known API Limitations

1. **Typo in Schema Field:** The production line filter key is spelled `ProdectionLine` (with an 'e'). Requests must preserve this spelling.
2. **Missing Shift Filter on Request:** Defect queries cannot supply a shift code in `FilterInfo.Filters`. Date range slicing (`StartDate` / `EndDate`) or post-retrieval filtering is mandatory.
3. **Internal Numeric ID Dependencies:** Fields such as `ProdectionLine`, `ProcessesId`, and `OrderNumber` require internal 64-bit IDs (e.g. `738620881702917` for `RenK-2`). A translation lookup table is required.
4. **Pagination:** Endpoints require explicit `CurrentPage` and `PageSize` parameters. Aggregations must handle paginated retrieval or request a page size covering the full target window.

---

## 5. Confidence Classification Summary

| Item | Classification | Rationale |
|---|---|---|
| Base URL `http://10.69.12.10:8000` | **CONFIRMED** | Directly observed working endpoint |
| Production API `POST /api/app/lot/lots` | **CONFIRMED** | Directly observed endpoint & payload |
| DefectData API `POST /api/app/report/787763718877829/data` | **CONFIRMED** | Directly observed endpoint & payload |
| DefectData UI Filters (9 specific fields) | **CONFIRMED** | Directly verified against UI interface |
| Typo field `ProdectionLine` | **CONFIRMED** | Verified in outgoing HTTP network payload |
| Filter `ExcludeDublicate` mapping to `Type` | **CONFIRMED** | Verified via controlled payload comparison |
| Shift Schedule (A: 07-15, B: 15-23, C: 23-07) | **CONFIRMED** | Directly read from Jinchen Base config |
| `Type="0"` produces 1 row per unique lot | **INFERRED** | 329 unique lots / 329 records observed (strong evidence) |
| `bad_quantity = COUNT(DISTINCT LotNumber)` | **INFERRED** | Strong candidate, requires business sign-off |
| `LastModificationTime` = Production Date | **TBD** | Ambiguous; UI uses it, but semantics are unconfirmed |
| Total Production = COUNT(Finished Lots) | **TBD** | Definition of completed production lot unconfirmed |
| WIP / Process Loss / Rework / FPY formulas | **TBD** | SRS open items D10, D11, D12 unresolved |

---

## 6. Blockers to Real MES Implementation

1. **Production Metric Semantic Sign-Off:** Need written confirmation on which `StateFlag` / timestamp defines an official "produced" module.
2. **Defect Deduplication Sign-Off:** Need written confirmation whether `bad_quantity` is defined as deduplicated lots (`Type="0"`) or specific severe defect categories.
3. **Internal ID Mapping Dictionary:** Need complete enumeration of Jinchen `ProductionLineId` values for all lines (`KM1`, `KM2`, `KM3`, `RenK-2`, etc.).
4. **Authentication & Session Lifecycle:** API session token management (login endpoints, expiration, headers) must be formally documented.

---

## 7. Next Implementation Steps (Post-Discovery)

1. Review and validate `docs/JINCHEN_FIELD_MAPPING.md`.
2. Secure stakeholder confirmation on `Total Production` state filters and `bad_quantity` deduplication logic.
3. Construct read-only lookup table for production line IDs.
4. Only after business confirmation: design `JinchenMESAdapter` implementing `MESAdapterBase`.
