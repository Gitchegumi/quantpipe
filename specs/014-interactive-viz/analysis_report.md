# Specification Analysis Report

## Summary

The analysis covering `spec.md`, `plan.md`, and `tasks.md` for feature `014-interactive-viz` reveals a generally high level of alignment, with a few coverage gaps regarding specific functional requirements (layer toggling) and edge case handling.

| ID  | Category       | Severity | Location(s)              | Summary                                                                     | Recommendation                                                         |
| --- | -------------- | -------- | ------------------------ | --------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| C1  | Coverage       | HIGH     | spec.md:FR-007, tasks.md | Missing specific task for "Toggle visibility of data layers" (FR-007).      | Add task to verify/enable legend or layer control in `interactive.py`. |
| A1  | Ambiguity      | MEDIUM   | tasks.md:T014            | "if needed" qualifier contradicts FR-006 strict requirement for tooltips.   | Rename T014 to "Configure tooltips to satisfy FR-006".                 |
| C2  | Coverage       | MEDIUM   | spec.md:Edge Cases       | No specific tasks to handle/verify edge cases (No Trades, Missing Data).    | Add sub-tasks or detailed checks in T005/T006/T010 for empty inputs.   |
| U1  | Underspecified | LOW      | plan.md:Performance      | "Performance Goals" rely on library capabilities without fallback strategy. | Ensure T016 checks performance early.                                  |

## Coverage Summary

| Requirement Key     | Has Task? | Task IDs   | Notes                                       |
| ------------------- | --------- | ---------- | ------------------------------------------- |
| FR-001 (CLI Flag)   | Yes       | T011       | Implemented in `run_backtest.py`            |
| FR-002 (OHLC)       | Yes       | T005, T007 | Core rendering                              |
| FR-003 (Trades)     | Yes       | T010       | Markers implementation                      |
| FR-004 (Indicators) | Yes       | T006, T009 | Indicator series                            |
| FR-005 (Zoom/Pan)   | Yes       | T013       | Configuration/Verification                  |
| FR-006 (Tooltips)   | Partially | T014       | Task implies optionality                    |
| FR-007 (Toggle)     | **No**    | -          | Implicit in library, but needs verification |
| FR-008 (Perf)       | Yes       | T016       | Validation task                             |

## Constitution Alignment

- **Strategy-First**: Adhered to (visualization decoupled).
- **Task Tracking**: `tasks.md` exists and follows format.
- **Risk Management**: N/A for visualization (read-only).
- **Code Quality**: Tasks include structure for clean code.

## Next Actions

1. **Remediation**:
   - Add task for FR-007 (Legend/Toggle).
   - Clarify T014 description.
   - Add edge case handling notes to T005/T010 (e.g., "Handle empty trade list gracefully").
2. **Proceed**:
   - After minor updates, proceed to `/speckit.implement`.

**Would you like me to apply these remediation fixes to `tasks.md`?**
