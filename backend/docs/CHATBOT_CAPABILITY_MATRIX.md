# Chatbot Capability Matrix

This matrix tracks the end-to-end functionality of user intents in Phase 2.5. A feature is marked as "Supported" only if the LLM correctly parses the intent, the backend orchestrator correctly fetches the data, the Metric Engine accurately computes the business value, and the LLM correctly generates the natural language response.

## Core Manufacturing Intents

| User Capability | Intent | Backend Support | Metric Engine | Mock Data | Status |
|----------------|--------|----------------|--------------|-----------|--------|
| Total production | `production_summary` | Yes | Yes | Yes | **Supported** |
| Production by shift | `production_by_shift` | Yes | Yes | Yes | **Supported** |
| Production by line | `production_by_line` | Yes | Yes | Yes | **Supported** |
| Production by machine | `machine_production` | No | No | No | **Unsupported** (Data tracked at Line level) |
| Highest-production machine | `machine_ranking` | No | No | No | **Unsupported** (Data tracked at Line level) |
| Defect rate | `defect_rate` | Yes | Yes | Yes | **Supported** |
| Defect summary | `defect_summary` | Yes | Yes | Yes | **Supported** |
| Production comparison | `production_comparison` | Yes | Yes | Yes | **Supported** (Compare dates, lines, shifts) |
| Yield | `yield_summary` | Yes | Yes | Yes | **Supported** |
| Scrap rate | `scrap_rate` | Yes | Yes | Yes | **Supported** |

## Pending Business Definitions (D10, D11, D12)

The following metrics are recognized by the system, but calculation is intentionally halted pending business rule finalization. They return a `definition_required` state.

| User Capability | Intent | Backend Support | Metric Engine | Mock Data | Status |
|----------------|--------|----------------|--------------|-----------|--------|
| Process loss | `process_loss` | Yes | Halt | Yes | **Definition Required** (D11) |
| WIP | `wip_summary` | Yes | Halt | Yes | **Definition Required** (D10) |
| Rework / Rework Rate | `rework_summary` | Yes | Halt | Yes | **Definition Required** (D12) |
| OEE | `oee_summary` | Yes | Halt | Yes | **Definition Required** |
| First Pass Yield (FPY) | `first_pass_yield` | Yes | Halt | Yes | **Definition Required** |

## Ambiguous & Out-of-Scope Intents

| User Capability | Intent | Status | Reason |
|----------------|--------|--------|--------|
| "How did we perform today?" | `clarification_needed` | **Clarification** | Vague query; asks user to clarify metric. |
| "What was our profit?" | `out_of_scope` | **Out of Scope** | Financial data is not tracked in the MES. |
| "Show me alerts" | `out_of_scope` | **Out of Scope** | Alerts are not in Phase 1 scope. |
