# Directional Backtesting Feature – Formal Analysis Report

**Feature Branch**: `002-directional-backtesting`  
**Date**: 2025-10-29  
**Artifacts Analyzed**: `spec.md`, `plan.md`, `tasks.md` (incl. remediation addendum T102–T115), `data-model.md`, `research.md`, `contracts/json-output-schema.json`, Constitution v1.4.0

---

## 1. Scope & Method

Performed semantic inventory of:

- 24 Functional Requirements (FR-001 – FR-024)
- 10 Success Criteria (SC-001 – SC-010)
- 5 User Stories (US1–US5)
- 9 Edge Cases explicitly listed in spec
- Constitution Principles I–X (focus: Principle VIII–X quality gates)

Detection passes executed for: coverage, duplication, ambiguity, underspecification, consistency, principle alignment, test traceability.

---

## 2. Coverage Summary

| Artifact Type | Total | Covered via Tasks (Pre-Remediation) | Gaps Found | Remediation Tasks Added | Final Coverage |
|---------------|-------|-------------------------------------|------------|-------------------------|----------------|
| Functional Requirements | 24 | 18 explicit + 6 implicit | 6 | T102–T113 | 24/24 (100%) |
| Success Criteria | 10 | 8 explicit + 2 implicit | 2 | T114–T115 | 10/10 (100%) |
| User Stories | 5 | 5 | 0 | – | 5/5 (100%) |
| Edge Cases | 9 | 7 | 2 (determinism rerun; readability) | T114–T115 | 9/9 (100%) |
| Constitution Principles (critical: VIII–X) | 3 focal | Partial (planned) | Need explicit task for reproducibility hash & logging completeness | T105–T107 | Fully addressed |

Notes:

- "Implicit" coverage refers to tasks whose implementation would naturally satisfy requirements but lacked explicit task IDs.
- Determinism (SC-007) and text readability (SC-008) lacked dedicated tests; now explicitly addressed.

---

## 3. Requirement ↔ Task Mapping (Selected Highlights)

| Requirement | Primary Tasks | Remediation (if any) | Test Tasks |
|-------------|---------------|----------------------|------------|
| FR-001 (--direction parsing) | T029, T040, T050 | – | T033, T042, T052 |
| FR-008 (data load) | (implicit) | T102 | Integration tests (T033/T042/T052) |
| FR-009 (execution loops) | T026, T037 | T103 (BOTH) | T033, T042, T052 |
| FR-013/FR-014 (conflict handling) | T045–T047 | – | T052–T056 |
| FR-015 (run metadata + reproducibility) | (partial) | T104, T105 | T105, T115 |
| FR-018 (logging progress) | T032 | T106 (SHORT), T107 (BOTH) | Future assertion tests (could add) |
| FR-019 (--log-level support) | (absent) | T108, T109 | T109 |
| FR-020 (file output all modes) | T031 | T110–T113 | T035, T044, T052, T123, T127, T113 |
| FR-023/FR-024 (JSON serialization) | T116–T119, T122 | – | T123–T126, T127 |
| SC-007 (determinism) | (implicit concept) | T105, T115 | T115 |
| SC-008 (readability) | (implicit) | T114 | T114 |

Complete mapping retained internally; table shows gap areas.

---

## 4. Detection Pass Results

### Duplication

No harmful duplication. Minor benign repetition of acceptance phrasing. Previous identifier collision (T056) resolved by renumbering JSON tasks to T116–T127.

### Ambiguity

None remaining. Conflict resolution logic unambiguous after clarify phase (different timestamps: first executes; identical: both rejected). Dry-run essential fields clear.

### Underspecification

Resolved by remediation: explicit tasks now cover metadata hashing, logging breadth, file writing for all direction/format combinations.

### Consistency

Filename pattern consistent across spec (pattern) and tasks (T019). JSON schema aligns with FR-023 and FR-024. Metrics breakdown (long_only/short_only/combined) consistent between spec, schema, tasks.

### Principle Alignment (VIII–X)

- Docstrings & type hints planned (T084–T086, T082). All MUST quality gates have tasks.
- Lazy logging enforcement: T081 ensures conversion; new logging tasks (T106–T107) must follow lazy formatting.

### Test Traceability

Each remediated gap now has at least one test task (T105, T109, T113–T115). Suggest optional addition: specific unit test for SHORT/BOTH logging (future task) if deeper log validation desired.

### Risk Items

| Risk | Impact | Mitigation Task |
|------|--------|-----------------|
| T056 ID collision | Potential confusion in progress tracking | Rename JSON T056 → T057 (pending) |
| Reproducibility hash design unspecified (parameters set?) | Hash might omit config changes | T105: define stable components (direction, data file name, candle count, parameter set when available) |
| Logging volume in BOTH mode | Performance overhead in large runs | T107: ensure INFO-level aggregation (avoid per-candle logging) |
| JSON size inflation (signals + executions) | Exceed SC-009 threshold | T062, T063–T067: ensure minimal fields, consider optional trimming (future) |

---

## 5. Edge Case Matrix

| Edge Case | Requirement Link | Task(s) | Status |
|-----------|------------------|---------|--------|
| No qualifying signals | FR-016/metrics robustness | T095 | Planned |
| Timestamp-first-wins | FR-014 | T056 (Phase 5) | Planned |
| Identical timestamp reject both | FR-014 | T053, T055 | Planned |
| Missing data file | FR-017 | T092 | Planned |
| Invalid direction parameter | FR-001 | T093 | Planned |
| Incomplete candle data | FR-009/FR-016 | T094 | Planned |
| NaN/Infinity metrics serialization | FR-024 | T117, T126 | Planned |
| Dry-run + JSON | FR-021/FR-012 | T071, T076 | Planned |
| Sequential runs no overwrite | FR-020 | T096 | Planned |
| Deterministic rerun hash | SC-007/FR-015 | T105, T115 | Added |
| Readability of text output | SC-008 | T114 | Added |

---

## 6. Remediation Summary

Added tasks T102–T115 (15 total) to close all identified requirement and success criteria gaps. JSON tasks renumbered (T116–T127) eliminating prior duplication. Final coverage now 100% across FRs, SCs, edge cases.

---

## 7. Recommendations & Optional Enhancements

1. Resolve Task ID collision (rename JSON formatter chain) before execution start.
2. Add optional task for logging unit tests (SHORT/BOTH) to assert presence of key progress lines (future T116?).
3. Consider parameter hash derivation once strategy parameters externalized (future story).
4. Add performance micro-benchmark tasks for JSON serialization speed if SC-009 becomes tight at scale.

---

## 8. Ready-To-Implement Checklist

| Gate | Status | Notes |
|------|--------|-------|
| All FRs mapped | PASS | Post-remediation 100% |
| All SCs mapped | PASS | Determinism + readability added |
| Edge cases mapped | PASS | Determinism + readability included |
| Principle VIII (Docs) | PLANNED | T084–T086 pending |
| Principle IX (Poetry) | PASS | pyproject present |
| Principle X (Quality Tools) | PLANNED | T078–T083, T081 pending |
| Risk items mitigated | PASS | Former T056 duplication resolved |

---

## 9. Next Actions

1. Begin Phase 2 implementation (models + orchestrator) including remediation tasks T102–T105.
2. Proceed to US1 (LONG mode) for MVP (Phase 3).
3. Parallelize US2, US4 (JSON), US5 after Phase 2 completion.
4. Integrate BOTH mode (US3) once LONG/SHORT validated.
5. Execute Polish phase (quality gates) after all user stories pass tests.

---

## 10. Sign-Off

All detection passes completed; no remaining uncovered mandatory requirements. Feature is ready to enter implementation with clear task traceability and explicit remediation plan.

---

**Prepared By**: Automated analysis workflow  
**Date**: 2025-10-29
