# Requirement to Task Mapping (Initial)

| FR | Description | Primary Tasks |
|----|-------------|---------------|
| FR-001 | Suite executes | T020–T022, T028 |
| FR-002 | Interfaces updated | T010, T017, T050 |
| FR-003 | Remove obsolete | T029–T034, T046 |
| FR-004 | Deterministic | T016, T035–T039 |
| FR-005 | EMA/ATR values | T020, T020a, T020b, T020c |
| FR-006 | Long & short signals | T021, T022 |
| FR-007 | Risk sizing edges | T019, T019a, T023, T024 |
| FR-008 | Timing mech | T018b, T040 |
| FR-009 | Flakiness stabilize | T026, T026a, T026b |
| FR-010 | Naming/docstrings | T014, T015, T027, T027a |
| FR-011 | Tier categorization | T009–T013, T028 |
| FR-012 | Lazy logging | T045 |

| SC | Description | Validation Tasks |
|----|-------------|------------------|
| SC-001 | All retained tests pass | T020–T024, T021–T022 |
| SC-002 | Controlled reduction | T033, T046 |
| SC-003 | Unit runtime <5s | T018b, T040 |
| SC-004 | Zero flakiness | T026, T026a, T026b |
| SC-005 | FR coverage | T028, mapping.md review |
| SC-006 | Integration runtime <30s | T041 |
| SC-007 | Performance runtime <120s | T042 |
| SC-008 | Tier enforcement | T009–T013, T028 |
| SC-009 | Flakiness definition satisfied | T026, T026a, T026b |
