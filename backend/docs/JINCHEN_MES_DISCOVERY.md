# Jinchen MES Technical Discovery

## Overview
This document summarizes the technical discovery findings for integrating the Renewsys MES AI Chatbot with the Jinchen MES data source.

The application architecture uses a normalized `MESProductionRecord` model and a `MockMESAdapter`. Phase 3 focuses on discovering the real Jinchen MES interface to eventually implement `JinchenMESAdapter`.

> **CRITICAL ARCHITECTURAL CONSTRAINTS:**
> - The chatbot intent, context, date handling, validation, metric engine, and security layers are **FROZEN**.
> - Do NOT implement `JinchenMESAdapter` prematurely.
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
- **Backend Connectivity Test (Directly Verified):** Direct HTTP connection from the local backend machine to `http://10.69.12.10:8000` results in a **ConnectTimeout**. The MES is currently accessible exclusively inside the remote UltraViewer session; direct network routing/VPN to the backend runtime is a required infrastructure step.

---

## 2. Phase 3.1 & 3.2 — API Discovery Results

### A. Production API — QueryLotReport
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/lot/lots`
- **Confidence:** **CONFIRMED** (Directly observed from API/UI)
- **Description:** Returns production lot records including lifecycle timestamps, process line identifiers, work orders, material codes, and status flags.
- **Request Filter Structure:**
  - Date filtering: `LastModificationTime` with operators `GreaterThanOrEqual` and `LessThanOrEqual`.
  - Date format: `"YYYY/MM/DD HH:mm:ss"`.
  - Sorting parameter: `"CreationTime desc,LotNumber desc"`.
- **Live Discovery Analysis (1-Month Window 2026/09/07 to 2026/10/06):**
  - Total records: **140,594** across the plant.
  - Returned queue items show `StateFlag = 1` and `StateFlagCode = "EnumLotState_WaitTrackIn"`.
  - Timestamps `TrackInTime` and `TrackOutTime` are `null` while in this waiting state.
  - Stations observed in queue: `EPE` (`738714999574533`), `Laminator` (`738715148627973`), `Framing-VI`, `OQC`.
  - Line ID `738616585908229` confirmed matching `ProductionLineCode = "RenK-1"`.
- **Historical Analysis (5 Sept – 4 Oct 2026 Export):**
  - Total records: 2,764 rows / 2,764 unique `LotNumber`s.
  - `Quantity`: exactly 1.0 on every row.
  - Production lines observed: `RenK-1` = 652, `RenK-2` = 2,086, `Renk-PDI` = 26.
  - States observed: `Waiting for Track In` = 2,030, `Finished` = 650, `Waiting for Track Out` = 84.
- **Deduction:** `QueryLotReport` without a state filter returns massive queues of intermediate/unprocessed WIP (140,594 records). A plain row count (`COUNT(*)`) over-counts incomplete lots. Completed production requires filtering by finished state (e.g. `EnumLotState_Finish`) or tracking track-out events at final stations (`Framing-VI`, `Packing`, `OQC`).

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
The Jinchen DefectData UI exposes **exactly nine (9)** request filters.

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

### D. Production Summary API — LotFinalDataReport
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/report/756398601302021/data`
- **UI Path:** `RPT-ReportManagement -> ProductionReport -> LotFinalDataReport`
- **Confidence:** **CONFIRMED** (Directly observed from API/UI)
- **Observed Filters:** `ShiftName`, `MaterialCode`, `LineCode`, `StartDate`, `EndDate`, `ProcessName`, `Grade`.
- **Response Fields:** `LotNumber`, `WorkOrderCode`, `MaterialCode`, `FinalLocationName`, `FinalProductionLineCode`, `FinalProcess`, `FinalGrade`, `FinalCreationTime`, `FinalCreator`, `MinGrade`, `minCreatorName`, `minCreationTime`.
- **Backend SQL Bug (CONFIRMED):** Supplying a `ShiftName` filter triggers a server error: `Invalid column name 'ShiftName'`. The backend SQL attempts to query `a.ShiftName`, which does not exist in the underlying table/view. Therefore, `ShiftName` **cannot** be passed as a request filter to this report.
- **Line Filter Test (RenK-1):** `LineCode = 738616585908229` between `2026/10/03 20:00:00` and `2026/10/04 08:00:00` returned `TotalCount = 831` records with `FinalProductionLineCode = RenK-1`. Final processes included `Framing-VI`, `OQC`, `EPE`.

### E. Confirmed Production Line ID Dictionary
The 64-bit internal IDs corresponding to each production line across Jinchen MES are:

| Production Line Code | Internal Line ID (`Int64`) | Typical User Name | Verification Status |
|---|---|---|---|
| `RenK-1` | `738616585908229` | Line 1 / KM1 | **CONFIRMED** |
| `RenK-2` | `738620881702917` | Line 2 / KM2 | **CONFIRMED** |
| `Line 3` (RenK-3) | `738620932063237` | Line 3 / KM3 | **CONFIRMED** |
| `Line 4` (PDI / Special) | `764804556390405` | Line 4 / PDI | **CONFIRMED** |

*(Notice: `ProcessName = 738629314535429` maps to "Main Process").*

### F. Shift Schedule & Timing
- **Shift A (Morning):** `07:00 – 15:00`
- **Shift B (Second):** `15:00 – 23:00`
- **Shift C (Night):** `23:00 – 07:00` (Crosses midnight)
- **Constraint:** Neither `DefectData` nor `LotFinalDataReport` supports a functional request-side shift filter. Shift-level reporting must be achieved via exact datetime slicing (`StartDate` / `EndDate`) or post-retrieval filtering on response fields.

---

## 3. Reconciliation & Semantic Findings

### G. Controlled Defect Deduplication Trial
- **Without Deduplication (`Type = "1"`, ExcludeDublicate = No):** 548 records, 329 unique lots. 149 lots had multiple defect entries, 13 exact duplicate rows.
- **With Deduplication (`Type = "0"`, ExcludeDublicate = Yes):** 329 records, 329 unique lots, 0 duplicate rows.
- **Finding:** Setting `Type = "0"` reliably produces 1 defect row per unique lot in tested sets.
- **Status:** **CANDIDATE / STRONG EVIDENCE** — Pending business confirmation before equating `bad_quantity = COUNT(DISTINCT LotNumber)`.

### H. Production ↔ Defect Reconciliation (3 Oct 2026 07:00–15:00)
- **Production Export (QueryLotReport):** 3,037 rows / 3,037 unique lots. Quantity = 1.
  - `RenK-2`: 2,230 lots | `RenK-1`: 781 lots | `Renk-PDI`: 26 lots.
  - States: `Waiting for Track In` = 2,133, `Finished` = 837, `Waiting for Track Out` = 67.
- **Defect Export (DefectData with Deduplication):** 596 defect records / 359 unique lots.
- **Correlation:** 358 of 359 defect lots matched rows in the production export.
- **Conclusion:** Defect lots correlate directly with module lots across the line, but total production cannot be defined as all lots in QueryLotReport because over 70% were still waiting for station entry.

---

## 4. Confidence Classification Summary

| Item | Classification | Rationale |
|---|---|---|
| Base URL `http://10.69.12.10:8000` | **CONFIRMED** | Directly observed working endpoint |
| QueryLotReport API `POST /api/app/lot/lots` | **CONFIRMED** | Directly observed endpoint & payload |
| DefectData API `POST /api/app/report/787763718877829/data` | **CONFIRMED** | Directly observed endpoint & payload |
| LotFinalDataReport API `POST /api/app/report/756398601302021/data` | **CONFIRMED** | Directly observed endpoint & payload |
| DefectData UI Filters (9 specific fields) | **CONFIRMED** | Directly verified against UI interface |
| Typo field `ProdectionLine` | **CONFIRMED** | Verified in outgoing HTTP network payload |
| Filter `ExcludeDublicate` mapping to `Type` | **CONFIRMED** | Verified via controlled payload comparison |
| LotFinalDataReport ShiftName Backend Bug | **CONFIRMED** | Directly reproduced SQL exception `Invalid column name 'ShiftName'` |
| Complete Line ID Dictionary (Lines 1 to 4) | **CONFIRMED** | Captured across four distinct line queries |
| Authentication: Bearer Token Scheme | **CONFIRMED** | Directly captured in client request headers |
| Shift Schedule (A: 07-15, B: 15-23, C: 23-07) | **CONFIRMED** | Directly read from Jinchen Base config |
| `Type="0"` produces 1 row per unique lot | **INFERRED** | 329 unique lots / 329 records observed (strong evidence) |
| `bad_quantity = COUNT(DISTINCT LotNumber)` | **INFERRED** | Strong candidate, requires business sign-off |
| Completed Production Output = `LotFinalDataReport` | **INFERRED** | 1,027 units verified for Shift A |
| WIP / Process Loss / Rework / FPY formulas | **TBD** | SRS open items D10, D11, D12 unresolved |

---

## 5. Development Gate & Remaining Items

**Items Resolved during Technical Discovery:**
- [x] Base URL & port (`http://10.69.12.10:8000`)
- [x] Authentication headers (`Authorization: Bearer <token>`, `X-Requested-With`, `X-Button-Permission: Search`, `Route`)
- [x] Shift definitions and datetime slicing
- [x] Complete Line ID dictionary (`RenK-1` = `738616585908229`, `RenK-2` = `738620881702917`, `Line 3` = `738620932063237`, `Line 4` = `764804556390405`)
- [x] Defect API endpoint, filters (`Type="0"`), and parameters
- [x] Production Summary endpoint (`LotFinalDataReport`) and schema (`FinalProcess`, `MinGrade`)

**Items Remaining Before Live Adapter Production Deployment:**
1. **Network Connectivity:** Establishing VPN/tunnel routing from the local backend machine to `10.69.12.10:8000`.
2. **Dedicated Service Account Token:** Dedicated non-expiring service account token provisioned by IT for `JINCHEN_API_TOKEN`.
3. **Formal Stakeholder Confirmation:** Final sign-off on whether plant management defines production output as all units in `LotFinalDataReport` (1,027 units) or units reaching the `Packing` station specifically.
