# Jinchen MES API Catalog

This document catalogs the specific Jinchen MES REST APIs identified for supporting the Renewsys AI Chatbot. 
Only APIs directly evaluated or required for chatbot manufacturing capabilities are documented here.

---

## 1. Production API — QueryLotReport (`/api/app/lot/lots`)

- **Chatbot Capability:** Lot Tracking, Candidate Production Output, Lifecycle Inspection.
- **Report Name:** QueryLotReport
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/lot/lots`
- **Authentication:** Session cookie / bearer token (TBD — service account pending).
- **Exposed UI Filters (CONFIRMED from live UI):**
- **Exposed UI Filters & API Request Mapping (CONFIRMED from live UI & DevTools):**
  The QueryLotReport UI exposes the following filters and serializes them into `FilterInfo.Filters`:
  1. `WorkOrder` → `WorkOrderId` / `WorkOrderCode`
  2. `Material` → `MaterialId` / `MaterialCode`
  3. `Grade` → `Grade`
  4. `ProductionLine` → `ProductionLineId` (`Equal`, e.g. `738620881702917` for RenK-2)
  5. `Equipment` → `EquipmentId`
  6. `Location` → `LocationId`
  7. `TechnologyGroup` → `TechnologyGroupId` (`Equal`, e.g. `738629838348293`)
  8. `Technology` → `TechnologyId`
  9. `TechnologyStep` → `TechnologyStepId` (`Operator: "Any"`, array value, e.g. `[738629420609541]`)
  10. `PackageNumber` → `PackageNumber`
  11. `StartTime` → `LastModificationTime` (`GreaterThanOrEqual`, format: `YYYY/MM/DD HH:mm:ss`)
  12. `EndTime` → `LastModificationTime` (`LessThanOrEqual`, format: `YYYY/MM/DD HH:mm:ss`)
  13. `LotNumbers` → `LotNumbers`
  *(Notice: There is NO dedicated State or Status filter on this UI screen).*

- **Station Filter Discovery Trial (CONFIRMED):**
  - Filtering for `ProductionLineId = 738620881702917` + `TechnologyGroupId = 738629838348293` + `TechnologyStepId = [738629420609541]` returned `{"TotalCount": 0, "Items": []}`.
  - **Reason:** In Jinchen MES, `QueryLotReport` reflects the **CURRENT** active station/state of each lot. If a lot has moved past that step, its current `TechnologyStepId` is no longer `738629420609541`.
  - Furthermore, `738620881702917` is the `DefectData` line ID for RenK-2; earlier we confirmed `QueryLotReport` uses line ID `738616585908229` for `RenK-1`.
  - **Crucial Takeaway:** `QueryLotReport` acts as a snapshot of where lots currently reside or were last modified, making it unreliable as a historical station production counter. Dedicated summary reports (like `LotFinalDataReport` or `ShopDeliveryReport`) or station movement logs are designed for historical output counting.
- **Observed Response Structure (DevTools Capture 2026-10-05):**
  ```json
  {
    "TotalCount": 140594,
    "Items": [
      {
        "TenantId": null,
        "OrgId": "690dc7dd-b0df-a1ac-0048-ef0d5f8f05a7",
        "IsActived": true,
        "LotNumber": "R5300039261959858",
        "OrgWorkOrderId": 852676277387397,
        "WorkOrderId": 852676277387397,
        "OrgWorkOrderCode": "0000012306",
        "WorkOrderCode": "0000012306",
        "MaterialId": 740103778447365,
        "MaterialCode": "RE620T2B2 G12R",
        "Grade": "A1",
        "Priority": 1,
        "QuantityInitial": 1.000000,
        "Quantity": 1.000000,
        "TechnologyGroupId": 738629838348293,
        "TechnologyId": 738629314535429,
        "TechnologyName": "Main Process",
        "TechnologyStepId": 738714999574533,
        "TechnologyStepName": "EPE",
        "LocationId": 738615012331525,
        "LocationName": "Renewsys Khopoli",
        "PreProductionLineId": 738616585908229,
        "ProductionLineId": 738616585908229,
        "ProductionLineCode": "RenK-1",
        "StartWaitTime": "2026/10/05 22:36:36",
        "StartProcessTime": null,
        "IsMainLot": true,
        "SplitFlag": false,
        "RepairFlag": false,
        "ReworkFlag": false,
        "HoldFlag": false,
        "ScrapFlag": false,
        "ShippedFlag": false,
        "DeletedFlag": false,
        "PackagedFlag": false,
        "StateFlag": 1,
        "StateFlagCode": "EnumLotState_WaitTrackIn",
        "OperateComputer": "10.69.20.22",
        "TrackInTime": null,
        "TrackOutTime": null,
        "ExecutionDuration": 0,
        "LastModificationTime": "2026/10/05 22:34:58",
        "CreationTime": "2026/10/04 16:11:20",
        "Id": 855839861608481
      }
    ]
  }
  ```
- **Key Fields & Meaning:**
  - `LotNumber`: Unique solar module serial / barcode identifier (e.g. `R5300039261959858`).
  - `ProductionLineCode`: Physical line label (`RenK-1`, `RenK-2`, `Renk-PDI`). LineId `738616585908229` matches `RenK-1`.
  - `Quantity` & `QuantityInitial`: Module quantity (always `1.000000` per module lot).
  - `StateFlag`: Integer code (e.g., `1`).
  - `StateFlagCode`: Exact enumeration string (e.g., `"EnumLotState_WaitTrackIn"`, `"EnumLotState_Finish"`).
  - `TechnologyStepName`: Process station (e.g. `EPE`, `Laminator`, `Framing-VI`, `OQC`).
  - `StartWaitTime`: Timestamp when lot entered waiting queue for the station.
  - `StartProcessTime`, `TrackInTime`, `TrackOutTime`: Processing timestamps (all `null` while `EnumLotState_WaitTrackIn`).
  - `CreationTime`: Initial lot generation timestamp (`YYYY/MM/DD HH:mm:ss`).
  - `LastModificationTime`: Timestamp used by default UI filter (`YYYY/MM/DD HH:mm:ss`).
- **Critical Production Semantics Finding:**
  - Over a 1-month window (`2026/09/07` to `2026/10/06`), the unfiltered query returns **140,594 records**.
  - All returned items at the top of the queue exhibit `StateFlag = 1` and `StateFlagCode = "EnumLotState_WaitTrackIn"`, with `TrackInTime = null` and `TrackOutTime = null`.
  - **Deduction:** Without filtering by state, `QueryLotReport` measures active inventory/WIP waiting across process steps, NOT completed production output.
  - To isolate completed production, filtering by `StateFlagCode` (e.g., `"EnumLotState_Finish"`) or track-out timestamp at a final station is strictly required.
- **Validation Status:** **CONFIRMED** endpoint, request filter syntax, pagination, sorting (`CreationTime desc,LotNumber desc`), and queue semantics; **UNRESOLVED** exact state filter string for completed modules.

---

## 2. Defect Reporting API — DefectData (`/api/app/report/787763718877829/data`)

- **Chatbot Capability:** Defect Summary, Bad Quantity, Defect Categories, Quality Breakdown.
- **Report Name:** DefectData Report
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/report/787763718877829/data`
- **HTTP Method:** `POST`
- **Request Format:**
  ```json
  {
    "CurrentPage": 1,
    "PageSize": 50,
    "FilterInfo": {
      "Logic": "And",
      "Filters": [
        { "Field": "StartDate", "Operator": "Equal", "Value": "2026-10-03 07:00:00" },
        { "Field": "EndDate", "Operator": "Equal", "Value": "2026-10-03 15:00:00" },
        { "Field": "ProdectionLine", "Operator": "Equal", "Value": 738620881702917 },
        { "Field": "Type", "Operator": "Equal", "Value": "0" }
      ]
    }
  }
  ```
- **Observed Response Structure:**
  ```json
  {
    "TotalCount": 329,
    "Items": [
      {
        "LotNumber": "R5300040261968210",
        "WorkOrderCode": "WO-20261003-01",
        "MaterialCode": "MOD-540W-BIFACIAL",
        "TechnologyName": "Cell Testing",
        "TechnologyStepName": "POST-EL",
        "ProductionLineCode": "RenK-2",
        "Laminator": "LAM-01",
        "Layup": "LAY-02",
        "Grade": "A2",
        "DefectCode": "EL08",
        "DefectDescription": "Micro-crack on cell 34",
        "DefectPosition": "Row 4, Col 6",
        "ShiftName": "Morning",
        "CreationTime": "2026-10-03 09:14:22",
        "UserName": "OPR_104"
      }
    ]
  }
  ```
- **Key Fields & Meaning:**
  - `LotNumber`: Serial of defective unit. Multiple rows can exist per unit if multiple defects are logged.
  - `ProdectionLine`: Request filter parameter (**literal typo in Jinchen API**; accepts internal 64-bit ID, e.g. `738620881702917` for `RenK-2`).
  - `Type`: Corresponds to UI filter `ExcludeDublicate` (`"0"` = Yes, `"1"` = No).
  - `ShiftName`: Output field indicating operational shift. **Cannot be filtered on request**.
- **Known Limitations:**
  - No request-side `Shift` parameter. Queries must slice `StartDate`/`EndDate` by shift hours.
  - A single module can have multiple defect rows (548 records vs 329 unique lots when `Type="1"`).
- **Validation Status:** **CONFIRMED** endpoint, filters, and deduplication behavior (`Type="0"`).

---

## 3. Production Summary API — LotFinalDataReport (`/api/app/report/756398601302021/data`)

- **Chatbot Capability:** Candidate Final Production Output, Completed Module Reporting.
- **Report Name:** LotFinalDataReport
- **UI Path:** `RPT-ReportManagement -> ProductionReport -> LotFinalDataReport`
- **Endpoint:** `POST http://10.69.12.10:8000/api/app/report/756398601302021/data`
- **HTTP Method:** `POST`
- **Exposed UI Filters (CONFIRMED from live UI):**
  1. `OrderNumber` (dropdown/search, serializes as `Field: "OrderNumber"`, `Operator: "Equal"`, internal Int64 ID e.g. `856187710886021`)
  2. `ShiftName` (dropdown, but **do not use** due to backend SQL bug)
  3. `MaterialCode`
  4. `StartDate` (`Operator: "Equal"`, format: `YYYY/MM/DD HH:mm:ss`)
  5. `EndDate` (`Operator: "Equal"`, format: `YYYY/MM/DD HH:mm:ss`)
  6. `ProcessName` (Dropdown options: `1: Main Process`, `2: Rework Process`, `3: Post-rework Process`. Note: This filters high-level process route, NOT individual station like Packing. When filtered, if backend views don't match the code, it may return 0).
  7. `LotNumber`
  *(Advanced Search expands additional fields like `LineCode`, `Grade`).*
- **Request Format Example:**
  ```json
  {
    "CurrentPage": 1,
    "PageSize": 50,
    "FilterInfo": {
      "Logic": "And",
      "Filters": [
        { "Field": "StartDate", "Operator": "Equal", "Value": "2026-10-03 20:00:00" },
        { "Field": "EndDate", "Operator": "Equal", "Value": "2026-10-04 08:00:00" },
        { "Field": "LineCode", "Operator": "Equal", "Value": 738616585908229 }
      ]
    }
  }
  ```
- **Observed Response Structure (Shift A Live Discovery 2026-10-03 07:00:00 to 15:00:00):**
  ```json
  {
    "TotalCount": 1027,
    "Items": [
      {
        "No": 1,
        "LotNumber": "R1400040260103133",
        "WorkOrderCode": "0000012311",
        "MaterialCode": "RE620T2B2 G12R",
        "FinalLocationName": "Renewsys Khopoli",
        "FinalProductionLineCode": "RenK-2",
        "FinalProcess": "Framing",
        "FinalGrade": "R1400040260103133",
        "FinalCreationTime": "2026-10-03T07:13:14.653",
        "FinalCreator": "90-VI-KM2-1",
        "MinGrade": "A1",
        "minCreatorName": "90-VI-KM2-1",
        "minCreationTime": "2026-10-03T07:13:14.653"
      },
      {
        "No": 12,
        "LotNumber": "R5300040261967010",
        "WorkOrderCode": "0000012238",
        "MaterialCode": "RE620T2B2 G12R",
        "FinalLocationName": "Renewsys Khopoli",
        "FinalProductionLineCode": "RenK-2",
        "FinalProcess": "Packing",
        "FinalGrade": "R5300040261967010",
        "FinalCreationTime": "2026-10-03T07:58:53.373",
        "FinalCreator": "Packing-201",
        "MinGrade": "A2",
        "minCreatorName": "Packing-201",
        "minCreationTime": "2026-10-03T07:58:53.373"
      }
    ]
  }
  ```
- **Key Fields & Semantics Discovered:**
  - `TotalCount`: **1,027 modules** completed across all stations in Shift A (`07:00–15:00` on 2026-10-03).
  - `FinalProcess`: Reflects the station where the module was recorded: `Packing` (final packaging), `Framing`, `EPE`, `OQC`.
  - `FinalProductionLineCode`: Physical line code (`RenK-2`, `RenK-1`).
  - `FinalGrade`: Notice that `FinalGrade` is populated with the `LotNumber` string, whereas `MinGrade` contains the actual quality classification (`"A1"`, `"A2"`, `"Z"`, `"Rework"`).
  - `FinalCreator` / `minCreatorName`: Machine station/operator ID (e.g. `Packing-201`, `90-VI-KM2-1`, `EAP`).
  - `FinalCreationTime`: ISO format `2026-10-03T07:13:14.653`.
- **Known Limitations & Bugs:**
  - **CRITICAL BACKEND BUG:** Applying `ShiftName` in `FilterInfo.Filters` causes server SQL error: `Invalid column name 'ShiftName'`. Do **NOT** send `ShiftName` to this endpoint. Always slice shifts using `StartDate` and `EndDate`.
  - Quality grade resides in `MinGrade`, not `FinalGrade`.
- **Confirmed Production Line IDs (Directly Observed across Payloads):**
  | Line Code / Name | Internal Line ID (`Int64`) | Source Report Endpoints | Confidence |
  |---|---|---|---|
  | `RenK-1` (KM1) | `738616585908229` | `LotFinalDataReport`, `QueryLotReport` | **CONFIRMED** |
  | `RenK-2` (KM2) | `738620881702917` | `LotFinalDataReport`, `DefectData`, `QueryLotReport` | **CONFIRMED** |
  | `Line 3` (KM3 / RenK-3) | `738620932063237` | `LotFinalDataReport` | **CONFIRMED** |
  | `Line 4` (PDI / Special) | `764804556390405` | `LotFinalDataReport` | **CONFIRMED** |

- **Validation Status:** **CONFIRMED** endpoint, exact shift output counts (1,027 modules in Shift A), stations, complete Line ID dictionary, and line codes.

---

## 4. HTTP Protocol & Authentication Specifications

All Jinchen MES REST APIs enforce the following client request headers (Directly Observed from DevTools capture):

### A. Authentication Scheme
- **Mechanism:** OAuth2 / OpenID Connect Bearer Token.
- **Header:** `Authorization: Bearer <token>`
- **Token Type:** JWT bearer access token issued upon user login.
- **Service Security Protocol:** The adapter must either accept an injected service bearer token (via `.env` variable `JINCHEN_API_TOKEN`) or obtain one via the Jinchen authentication service.

### B. Required Request Headers
```http
POST /api/app/report/756398601302021/data HTTP/1.1
Host: 10.69.12.10:8000
Content-Type: application/json;charset=UTF-8
Accept: application/json, text/plain, */*
Authorization: Bearer <token>
X-Requested-With: XMLHttpRequest
X-Button-Permission: Search
Route: /RPT-ReportManagement/ProductionReport/LotFinalDataReport
Referer: http://10.69.12.10:8000/RPT-ReportManagement/ProductionReport/LotFinalDataReport?Id=756398601302021
Origin: http://10.69.12.10:8000
```

> **CLIENT HEADER RULE:** When implementing HTTP calls in `httpx` within `JinchenMESAdapter`, include `X-Requested-With: XMLHttpRequest`, `X-Button-Permission: Search`, and `Route` alongside the `Authorization` header to prevent ASP.NET permission rejection.
