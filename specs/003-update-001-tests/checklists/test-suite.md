# Requirements Quality Checklist: 001 Test Suite Alignment

**Purpose**: "Unit tests for English" validating clarity, completeness, measurability, and consistency of written requirements for updated 001 test suite and referenced strategy behaviors.
**Created**: 2025-10-30
**Scope Selection**: Test suite + referenced strategy behaviors (signals, indicators, risk)
**Depth Level**: Lightweight reviewer aid
**Primary Audience**: Author (pre-commit self-check)

## Requirement Completeness

- [ ] CHK001 Are all test tier definitions (unit/integration/performance) documented with explicit time thresholds? [Completeness, Spec §Functional FR-011]
- [ ] CHK002 Are deterministic fixture requirements (types of price scenarios: trend, flat, outlier) explicitly listed? [Completeness, Spec §Edge Cases]
- [ ] CHK003 Are requirements covering both long and short signal criteria present (or explicitly excluded)? [Completeness, Spec §FR-006]
- [ ] CHK004 Are risk sizing scenarios (normal, minimal balance, high volatility) all enumerated? [Completeness, Spec §FR-007]
- [ ] CHK005 Are flakiness stabilization requirements specified (what constitutes flaky and resolution expectation)? [Completeness, Spec §FR-009]
- [ ] CHK006 Is there a requirement ensuring docstrings for all new/modified test utilities? [Completeness, Spec §FR-010]

## Requirement Clarity

- [ ] CHK007 Is the term "deterministic" clarified (no randomness unless seeded) to avoid ambiguity? [Clarity, Spec §FR-004]
- [ ] CHK008 Are time thresholds (<5s, <30s, <120s) unambiguous and tied to total tier runtime vs per-test? [Clarity, Spec §FR-011]
- [ ] CHK009 Is expected fixture row count range (10–300 rows) clearly stated? [Clarity, Quickstart §Fixture Design]
- [ ] CHK010 Are criteria for removing a test (obsolete/redundant) explicitly defined (deprecated interface or duplicate assertions)? [Clarity, Spec §FR-003]
- [ ] CHK011 Is definition of "redundant" (overlapping identical assertions) clear enough to act on? [Ambiguity, Spec §FR-003]
- [ ] CHK012 Are indicator validation expectations (e.g., EMA warm-up stable value point) precisely described? [Clarity, Spec §FR-005]

## Requirement Consistency

- [ ] CHK013 Do performance thresholds (SC-003..SC-007) match tier definitions (FR-011) without conflict? [Consistency, Spec §Success Criteria]
- [ ] CHK014 Are runtime goals consistent between Quickstart and Success Criteria sections? [Consistency, Quickstart vs Spec §SC]
- [ ] CHK015 Do edge cases listed align with risk and indicator test coverage (no contradictions)? [Consistency, Spec §Edge Cases]
- [ ] CHK016 Are naming conventions consistent across research, contracts/test-tiering, and tasks? [Consistency, Research vs Contracts]

## Acceptance Criteria Quality / Measurability

- [ ] CHK017 Are all Success Criteria quantifiable (percent, time, counts) with no vague adjectives? [Measurability, Spec §SC-001..SC-007]
- [ ] CHK018 Can flakiness definition be objectively measured (e.g., stable across 3 consecutive runs)? [Measurability, Research §Flakiness]
- [ ] CHK019 Is test count reduction limit (≤30%) clearly measurable and traceable? [Measurability, Spec §SC-002]
- [ ] CHK020 Are indicator outcome expectations measurable (exact value comparisons) rather than qualitative? [Measurability, Spec §FR-005]

## Scenario Coverage

- [ ] CHK021 Are primary strategy behavior scenarios (signal generation, risk sizing, indicator calculation) all represented? [Coverage, Spec §User Story 1]
- [ ] CHK022 Are audit/removal scenarios represented for obsolete tests? [Coverage, Spec §User Story 2]
- [ ] CHK023 Are fixture introduction and runtime improvement scenarios covered? [Coverage, Spec §User Story 3]
- [ ] CHK024 Are negative scenarios (e.g., outlier candle, short dataset) documented? [Coverage, Spec §Edge Cases]

## Edge Case Coverage

- [ ] CHK025 Are dataset shorter-than-lookback handling expectations defined (warm-up vs failure)? [Edge Case, Spec §Edge Cases]
- [ ] CHK026 Are zero volatility (flat prices) behavior expectations specified (no false signals)? [Edge Case, Spec §Edge Cases]
- [ ] CHK027 Is extreme outlier candle handling requirement explicit (no overflow/division errors)? [Edge Case, Spec §Edge Cases]
- [ ] CHK028 Is behavior for missing optional columns (volume) clearly addressed? [Edge Case, Spec §Edge Cases]

## Non-Functional Requirements

- [ ] CHK029 Are performance tiers' isolation requirements (not in default fast CI run) specified? [Non-Functional, Contracts §Application Rules]
- [ ] CHK030 Are determinism and seeding requirements documented across all tiers? [Non-Functional, Spec §FR-004 / Contracts §Determinism]
- [ ] CHK031 Is logging standard (lazy formatting) reaffirmed for any test helpers? [Non-Functional, Constitution Principle X]

## Dependencies & Assumptions

- [ ] CHK032 Are assumptions about stable public interfaces (strategy, risk modules) explicitly noted? [Assumption, Spec §Assumptions]
- [ ] CHK033 Are fixture dependencies (indicators rely on OHLC order) captured? [Dependency, Data Model §Fixture Price Series]
- [ ] CHK034 Is need for pytest markers dependency explicitly stated (markers required before runtime assertions)? [Dependency, Plan §Technical Context]

## Ambiguities & Conflicts

- [ ] CHK035 Is any ambiguity remaining about what constitutes a "flaky" test beyond stability across runs? [Ambiguity, Research §Flakiness]
- [ ] CHK036 Are any conflicts between test removal criteria and redundancy consolidation tasks? [Conflict, Spec §FR-003 vs Tasks]
- [ ] CHK037 Is threshold interpretation (total suite vs per-test) fully resolved for performance metrics? [Ambiguity, Spec §FR-011]
- [ ] CHK038 Are any terms ("deterministic", "redundant") lacking formal glossary definitions? [Ambiguity, Research]

## Traceability & ID Scheme

- [ ] CHK039 Do all functional requirements (FR-001..FR-011) have at least one mapped test task? [Traceability, Tasks.md]
- [ ] CHK040 Are success criteria mapped to validation tasks (e.g., runtime assertion tasks T040–T042)? [Traceability, Tasks.md vs Spec §SC]
- [ ] CHK041 Is there a documented location for removed test justifications (commit body + removal-notes.md)? [Traceability, Tasks T029–T034]

## Review Readiness

- [ ] CHK042 Can a reviewer confirm completeness using only this checklist without opening unrelated docs? [Review Readiness]
- [ ] CHK043 Are high-risk areas (risk sizing, performance tiers) highlighted sufficiently for scrutiny? [Review Readiness]
- [ ] CHK044 Does the checklist avoid implementation verbs (verify/test/confirm) entirely? [Review Readiness]

## Consolidation & Scope Check

- [ ] CHK045 Are non-scope items (new strategy logic) explicitly excluded? [Scope, Spec §Out of Scope]
- [ ] CHK046 Is scope of fixture sizes (10–300 rows) consistently applied across docs? [Consistency, Quickstart vs Data Model]
- [ ] CHK047 Are criteria for test count reduction documentation (≤30%) unambiguous for reviewer sign-off? [Clarity, Spec §SC-002]

## Exit Conditions

- [ ] CHK048 Are all ambiguities (CHK011, CHK035, CHK037, CHK038) either clarified or queued for follow-up before implementation? [Exit]
- [ ] CHK049 Are measurable success criteria (SC-001..SC-007) all traceable to tasks (T040–T042 etc.)? [Exit]
- [ ] CHK050 Is readiness for implementation (tasks T001–T028 for MVP) documented clearly? [Exit, Tasks.md]
