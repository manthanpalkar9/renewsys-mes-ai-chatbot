# Jinchen MES Business Rules & Metric Specifications

This document defines the formal business rules, formulas, candidate mappings, and unresolved criteria for computing manufacturing metrics against Jinchen MES data.

---

## 1. Metric: Total Production / Output

- **Business Definition:** Count of solar modules successfully produced/completed within a defined timeframe and line/shift.
- **Candidate Data Sources:**
  - *Candidate 1:* `POST /api/app/lot/lots` (QueryLotReport) filtered by `StateFlag = 'Finished'` or specific completion station.
  - *Candidate 2:* `POST /api/app/report/756398601302021/data` (LotFinalDataReport) filtered by date bounds and LineCode.
- **Timestamp Semantics:**
  - Jinchen UI filters on `LastModificationTime`.
  - Production records show `TrackOutTime` and `CreationTime`.
  - *Status:* **UNRESOLVED**. Need business confirmation whether completion time (`TrackOutTime`) or `LastModificationTime` defines the reporting date.
- **Quantity Semantics:**
  - Observed data consistently shows `Quantity = 1` per lot row across 2,764 historical records.
  - Total production is expected to be `COUNT(distinct completed lots)` or `SUM(Quantity)`.
- **Validation Evidence:**
  - Reconciliation test (3 Oct 2026 07:00–15:00): QueryLotReport returned 3,037 lots, of which only 837 were in state `Finished` (2,133 were `Waiting for Track In`, 67 `Waiting for Track Out`).
  - LotFinalDataReport RenK-1 (3–4 Oct 2026): returned 831 records across final stations (`Framing-VI`, `OQC`, `EPE`).
- **Unresolved Questions:**
  1. Does "Total Production" mean modules passing the final station (e.g. `Packing` / `OQC`), or modules in state `Finished`?
  2. Does QueryLotReport or LotFinalDataReport serve as the authoritative source of truth for plant management?

---

## 2. Metric: Bad Quantity (Defective Modules)

- **Business Definition:** Total unique modules flagged with an inspection defect during the operational period.
- **Source API:** `POST /api/app/report/787763718877829/data` (DefectData Report).
- **Filters:**
  - `StartDate`: Start of shift/day (`YYYY-MM-DD HH:mm:ss`)
  - `EndDate`: End of shift/day (`YYYY-MM-DD HH:mm:ss`)
  - `ProdectionLine`: API-specific line ID (e.g. `738620881702917` for RenK-2)
  - `Type`: `"0"` (`ExcludeDublicate = Yes`)
- **Formula:**
  - Candidate: `COUNT(DISTINCT LotNumber)` or `TotalCount` when `Type = "0"`.
- **Validation Evidence:**
  - Controlled trial (548 defect records without deduplication):
    - `ExcludeDublicate = No` (`Type = "1"`): 548 rows across 329 unique lots (149 lots had multiple defect logs; 13 exact duplicates).
    - `ExcludeDublicate = Yes` (`Type = "0"`): exactly 329 rows across 329 unique lots (0 duplicates).
- **Unresolved Questions:**
  - Does business define Bad Quantity as all modules logged with any defect, or only modules failing re-inspection or assigned specific low grades (e.g. Grade B, Scrap)?

---

## 3. Metric: Defect Rate (%)

- **Business Definition:** Percentage of defective modules relative to total production.
- **Formula:**
  $$\text{Defect Rate} = \left(\frac{\text{Bad Quantity}}{\text{Total Production}}\right) \times 100$$
- **Numerator:** Unique defective lots from DefectData (`Type = "0"`).
- **Denominator:** Confirmed Total Production for the exact same timeframe and line.
- **Arithmetic Edge Cases:**
  - If Total Production = 0: return `null` / controlled "No production recorded" response (prevent division by zero).
- **Unresolved Question:**
  - Requires resolution of Metric 1 (Total Production denominator) to guarantee mathematical consistency.

---

## 4. Metric: Scrap Quantity & Scrap Rate

- **Business Definition:** Modules damaged beyond repair or officially scrapped.
- **Candidate Data Sources:**
  - QueryLotReport: `ScrapFlag = true` / `ScrapFlag = 1`.
  - DefectData: defect records with disposition / grade = Scrap.
- **Status:** **DEFINITION_REQUIRED** (SRS Open Issue). Pending business confirmation of data source.

---

## 5. Metrics: WIP, Process Loss, Rework, OEE, FPY

- **WIP (Work In Progress — SRS D10):** Candidate from QueryLotReport lots with state `Waiting for Track In` / `Waiting for Track Out` / `In Process`. Status: **DEFINITION_REQUIRED**.
- **Process Loss (SRS D11):** Status: **DEFINITION_REQUIRED**.
- **Rework / Repair (SRS D12):** Candidate from QueryLotReport `RepairFlag = true` or `ReworkFlag = true`. Status: **DEFINITION_REQUIRED**.
- **OEE & FPY:** Status: **DEFINITION_REQUIRED**. Require machine availability logs, cycle times, and scrap/rework loops not yet confirmed in Jinchen APIs.

---

## 6. Shift Assignment & Timezone Rules

- **Confirmed Shift Windows:**
  - **Shift A (Morning):** `07:00 – 15:00`
  - **Shift B (Second):** `15:00 – 23:00`
  - **Shift C (Night):** `23:00 – 07:00` (crosses midnight into calendar day + 1)
- **Shift Filtering Strategy:**
  - *DefectData:* Does not support request-side shift filtering. The adapter must compute exact start and end datetimes covering the shift.
  - *LotFinalDataReport:* Passing `ShiftName` causes a fatal SQL error on the backend (`Invalid column name 'ShiftName'`). Date slicing must be used instead.
- **Timezone:** **UNRESOLVED**. Server timezone (IST vs UTC vs CST) must be confirmed to ensure timestamp slices match factory floor reality.
