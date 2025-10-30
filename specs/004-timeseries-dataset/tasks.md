# Task Checklist: Time Series Dataset Preparation

**Branch**: 004-timeseries-dataset | **Spec**: specs/004-timeseries-dataset/spec.md | **Plan**: specs/004-timeseries-dataset/plan.md

## Phase 1: Setup

- [ ] T001 Ensure Poetry environment up to date (`pyproject.toml`, lock) – verify Python 3.11
- [ ] T002 Add placeholder CLI entry point for dataset build in `src/cli/__init__.py`
- [ ] T003 Create module scaffold `src/io/dataset_builder.py` for build orchestration
- [ ] T004 Configure logging pattern (lazy formatting) reference in `src/backtest/observability.py`
- [ ] T005 Create synthetic raw fixture directory `tests/fixtures/raw/eurusd/` with minimal CSV (≥600 rows) for testing

## Phase 2: Foundational

- [ ] T006 Implement symbol discovery function in `src/io/dataset_builder.py` (scan `price_data/raw/*/`)
- [ ] T007 Implement raw file schema validator in `src/io/dataset_builder.py` (timestamp + OHLCV columns)
- [ ] T008 Implement raw merge & sort routine in `src/io/dataset_builder.py` (dedup duplicates) capturing gap/overlap counts
- [ ] T009 Implement deterministic partitioning function in `src/io/dataset_builder.py` (floor 80% test, remainder validation)
- [ ] T010 Implement metadata record builder in `src/io/dataset_builder.py` (JSON structure per spec)
- [ ] T011 Implement consolidated summary builder in `src/io/dataset_builder.py` (aggregate counts & durations)
- [ ] T012 Implement file output writers (CSV partitions + metadata + summary) in `src/io/dataset_builder.py`
- [ ] T013 Add pydantic model definitions for MetadataRecord & BuildSummary in `src/models/metadata.py`
- [ ] T014 Add gap/overlap detection helper in `src/io/dataset_builder.py` (silent gap counting, explicit overlap reporting)

## Phase 3: User Story 1 (P1) Generate Chronological Split

- [ ] T015 [US1] Integrate all foundational components into `build_symbol_dataset` function in `src/io/dataset_builder.py`
- [ ] T016 [US1] Add CLI command `build-dataset` in `src/cli/dataset.py` invoking symbol build for single symbol
- [ ] T017 [US1] Add CLI option for `--symbol <symbol>` to restrict build to one symbol
- [ ] T018 [US1] Implement unit test for partition size logic in `tests/unit/test_dataset_split.py`
- [ ] T019 [US1] Implement unit test for metadata correctness in `tests/unit/test_metadata_generation.py`
- [ ] T020 [US1] Implement integration test single-symbol build in `tests/integration/test_single_symbol_build.py`
- [ ] T021 [US1] Update quickstart examples with single-symbol build usage in `specs/004-timeseries-dataset/quickstart.md`

## Phase 4: User Story 2 (P2) Multi-Symbol Processing

- [ ] T022 [US2] Add multi-symbol build orchestration `build_all_symbols` in `src/io/dataset_builder.py`
- [ ] T023 [US2] Extend CLI `build-dataset` to support `--all` and optional `--force` flags in `src/cli/dataset.py`
- [ ] T024 [US2] Implement integration test multi-symbol build in `tests/integration/test_multi_symbol_build.py`
- [ ] T025 [US2] Implement performance test with synthetic large dataset in `tests/performance/test_large_build_timing.py`
- [ ] T026 [US2] Implement summary validation unit test in `tests/unit/test_summary_generation.py`
- [ ] T027 [US2] Document multi-symbol usage and force rebuild option in `quickstart.md`

## Phase 5: User Story 3 (P3) Backtest Integration

- [ ] T028 [US3] Refactor backtest data loading to add partition-aware loader in `src/backtest/orchestrator.py`
- [ ] T029 [US3] Modify backtest metrics ingestion to separate test vs validation metrics in `src/backtest/metrics_ingest.py`
- [ ] T030 [US3] Add validation metrics output structure in `src/backtest/metrics.py`
- [ ] T031 [US3] Implement guard/warning when partitions missing in `src/backtest/orchestrator.py`
- [ ] T032 [US3] Add CLI/backtest mode flag `--mode split` in `src/cli/backtest.py`
- [ ] T033 [US3] Implement integration test backtest using partitions in `tests/integration/test_backtest_split_mode.py`
- [ ] T034 [US3] Update README with partition-based backtest description in `README.md`

## Final Phase: Polish & Cross-Cutting

- [ ] T035 Add docstrings & type hints pass across new files (`src/io/dataset_builder.py`, `src/models/metadata.py`)
- [ ] T036 Add logging improvements (summary table) in `src/io/dataset_builder.py`
- [ ] T037 Add reproducibility notes (metadata references) in `src/backtest/reproducibility.py`
- [ ] T038 Run quality gates (Black, Ruff, Pylint, pytest, Markdownlint) CI verification script
- [ ] T039 Optimize merge routine for memory if needed (chunking) in `src/io/dataset_builder.py`
- [ ] T040 Add README performance expectations section in `README.md`
- [ ] T041 Add unit test ensuring no gap warnings emitted (only overlaps) in `tests/unit/test_gap_warning_suppression.py`

## Dependencies / Story Order

1. Setup → Foundational → US1 → US2 → US3 → Polish
2. US2 depends on foundational + US1 functions validated
3. US3 depends on US1 partitions existing

## Parallel Execution Examples

- [ ] T008 [P] and T010 [P] can proceed after T007 validation logic finalized (different areas)
- [ ] T018 [P] and T019 [P] unit tests parallel (independent test files)
- [ ] T024 [P] integration multi-symbol and T025 [P] performance test generation can start after T022
- [ ] T028 [P] refactor orchestrator and T030 [P] metrics output changes (distinct files) after partitions stable

## Independent Test Criteria by Story

- US1: Single symbol build creates correct partitions & metadata; tests T018–T020 pass.
- US2: Multi-symbol build summary accurate; performance test within threshold; tests T024–T026 pass.
- US3: Backtest produces separate test/validation metrics; missing partitions produce warning; tests T028–T033 pass.

## MVP Scope

Implement through US1 (Tasks T001–T021). Provides usable dataset partitions for a single symbol.

## Format Validation

All tasks follow `- [ ] T### [P]? [USn]? Description with file path` pattern.
