# Changelog

All notable changes to the trading-strategies project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Feature 006: Multi-Strategy Backtesting Framework (2025-11-04)

- **Multi-Strategy Execution & Aggregation**
  - Strategy registry with tags/version metadata support
  - Weighted portfolio aggregation with configurable strategy weights
  - Per-strategy risk limit configuration and enforcement
  - Portfolio-level global abort on drawdown breaches
  - Net exposure aggregation by instrument
  - Deterministic run IDs and manifest hashing for reproducibility

- **CLI Enhancements**
  - `--register-strategy` flag for strategy registration
  - `--list-strategies` flag to display registered strategies
  - `--strategies` flag for multi-strategy selection
  - `--weights` flag for custom strategy weighting
  - `--aggregate/--no-aggregate` flags for portfolio aggregation control
  - Strategy filtering by names and tags with set operations

- **Configuration System**
  - Configuration override system (`merge_config`, `apply_strategy_overrides`)
  - Per-strategy parameter customization
  - Risk limit extraction from configuration
  - Validation early: unknown strategies rejected before execution

- **Observability & Quality**
  - OpenAPI contract validation (18 tests)
  - Logging standards enforcement (W1203 compliance, 8 tests)
  - Pylint quality gate script (≥8.0/10 threshold)
  - Reliability test harness (100% pass rate over 10 iterations)
  - Rich progress bar for data ingestion with gap counter
  - Correlation analysis deferral documented (FR-022)

- **Test Coverage**
  - 161 tests passing (45 unit + 65 integration + 20 performance + 18 contract + 13 other)
  - Determinism validation (8 tests)
  - Multi-strategy baseline execution tests
  - Weights validation and fallback tests
  - Strategy filtering and selection tests

### Fixed - Feature 006: CSV Processing & User Experience (2025-11-04)

- **CSV Preprocessing Issues**
  - Fixed TypeError when concatenating mixed-type date/time columns in MetaTrader CSV
  - Added format detection to skip conversion for already-processed CSV files
  - Added `dtype=str` to prevent mixed type warnings during ingestion
  - Removed duplicate `test_reproducibility.py` file causing pytest import errors

- **Column Name Compatibility**
  - Updated ingestion to accept both 'timestamp' and 'timestamp_utc' column names
  - Automatic column renaming for internal consistency
  - Better error messages when timestamp column is missing

- **Logging & Progress**
  - Changed gap warnings from WARNING to DEBUG level (per spec 004-timeseries-dataset)
  - Added rich progress bar showing candle count and gaps detected
  - Progress enabled for CLI (`show_progress=True`), disabled for tests (`show_progress=False`)
  - Reduced terminal clutter: 327K warnings → single progress line + summary
  - Output example: `Ingesting 6,922,364 candles ------------------------------ 100% • 327142 gaps`

### Changed - Feature 005: Documentation Restructure (2025-11-03)

- Separated end-user and contributor concerns:
  - Trimmed `README.md` to overview, 3-command Quick Start, minimal CLI usage, and documentation links.
  - Migrated environment setup, quality gates, test strategy, branching workflow, and logging rules into contributor guide (now `CONTRIBUTING.md`).
- Introduced `docs/` directory for conceptual documentation:
  - `docs/strategies.md` (strategy summaries & spec pointers)
  - `docs/backtesting.md` (dataset & metrics methodology)
  - `docs/structure.md` (repository layout reference)
- Added feature specification `specs/005-docs-restructure/spec.md` capturing requirements & success metrics.
- Ensured internal links updated and redundant sections removed from README.
- Added this CHANGELOG entry documenting rationale and scope.

### Added - Feature 004: Time Series Dataset Preparation (2025-10-30)

- **Dataset Building Infrastructure** (Phase 1-2: T001-T014)
  - Added `src/io/dataset_builder.py` with complete dataset orchestration
  - Implements symbol discovery, schema validation, merge/sort with deduplication
  - Deterministic 80/20 temporal partitioning (test/validation splits)
  - Gap and overlap detection with appropriate logging levels
  - Added `src/models/metadata.py` with MetadataRecord and BuildSummary models
  - Comprehensive metadata tracking for reproducibility

- **Single-Symbol Dataset CLI** (Phase 3: T015-T021)
  - Added `src/cli/build_dataset.py` CLI for dataset generation
  - Support for `--symbol <name>` to build specific symbol datasets
  - Unit tests for partition logic in `tests/unit/test_dataset_split.py`
  - Unit tests for metadata generation in `tests/unit/test_metadata_generation.py`
  - Integration tests in `tests/integration/test_single_symbol_build.py`
  - Updated quickstart documentation with usage examples

- **Multi-Symbol Processing** (Phase 4: T022-T027)
  - Extended CLI with `--all` flag for batch processing all symbols
  - Added `--force` flag for rebuild capability
  - Multi-symbol orchestration in `build_all_symbols()`
  - Integration tests in `tests/integration/test_multi_symbol_build.py`
  - Performance tests in `tests/performance/test_large_build_timing.py`
  - Verified <2 min for 1M rows (actual: 7.22s - 16x faster)
  - Summary validation tests in `tests/unit/test_summary_generation.py`

- **Backtest Integration** (Phase 5: T028-T034)
  - Added `src/io/partition_loader.py` for partition-aware data loading
  - Extended `src/models/directional.py` with PartitionMetrics and SplitModeResult
  - Added split-mode formatters in `src/io/formatters.py`
  - Partition existence guards and helpful error messages
  - Added `src/cli/run_split_backtest.py` for test/validation backtesting
  - Integration tests in `tests/integration/test_backtest_split_mode.py`
  - Updated README with partition-based workflow documentation

- **Quality & Performance** (Final Phase: T035-T041)
  - Verified complete docstrings and type hints across all modules
  - Rich table formatting for build summaries (already implemented)
  - Added partition metadata documentation to `src/backtest/reproducibility.py`
  - Quality gates: Black ✓, Pylint 9.56/10 ✓, pytest 390 passing ✓
  - Performance benchmarks added to README (1M rows in <10s)
  - Created `tests/unit/test_gap_warning_levels.py` verifying logging behavior
  - Fixed `test_flakiness_smoke.py` hang with pytest markers

- **Utilities**
  - Added `scripts/convert_mt_format.py` for MetaTrader CSV conversion
  - Converts headerless MT format to standard timestamp+OHLCV format
  - Batch processing support for entire directories

- **Testing**
  - 78 tests passing for feature-004 functionality
  - Performance validated: 8.6M rows processed in 54 seconds
  - Memory efficient: ~200MB for 1M rows, no chunking needed

### Added - Phase 6: Polish & Cross-Cutting (2025-10-29)

- **Statistical Significance Testing** (T055)
  - Added `tests/integration/test_significance.py` with bootstrap and permutation test harness
  - Implements p-value computation for Sharpe ratio and expectancy validation
  - Includes comprehensive test coverage for edge cases and significance thresholds

- **Adaptive Position Sizing** (T056)
  - Added `src/risk/adaptive_sizing.py` placeholder for volatility-based sizing
  - Includes Kelly criterion and portfolio heat multiplier functions
  - Reserved for future integration with volatility regime classifier

- **Stochastic RSI Indicator** (T057)
  - Added `src/indicators/stoch_rsi.py` for enhanced momentum detection
  - Computes %K and %D lines with smoothing
  - Includes oversold/overbought detection and crossover signals
  - Optional enhancement for reversal confirmation

- **Higher Timeframe Filter** (T058)
  - Added `src/strategy/trend_pullback/htf_filter.py` for multi-timeframe analysis
  - Implements EMA alignment checking on higher timeframe (FR-016, FR-028)
  - Includes candle aggregation and timeframe conversion utilities
  - Prevents counter-trend trades based on HTF context

- **Configuration Documentation** (T059)
  - Enhanced README.md with comprehensive configuration section
  - Documented all strategy parameters with defaults and descriptions
  - Added environment variable configuration guide
  - Included example code snippets for parameter setup

- **Code Quality Tooling** (T060, T061)
  - Added `.ruff.toml` with comprehensive linting rules for Python 3.11
  - Added `.pre-commit-config.yaml` for automated quality checks
  - Configured Black, Ruff, Pylint integration
  - Enabled pre-commit hooks for trailing whitespace, YAML/TOML validation

- **CLI Documentation** (T062)
  - Enhanced `src/cli/__init__.py` with comprehensive usage documentation
  - Documented all CLI commands, options, and examples
  - Added quick start guide for running backtests
  - Included configuration and environment variable references

- **Dry-Run Mode** (T063)
  - Added `--dry-run` flag to `src/cli/run_backtest.py` (FR-024)
  - Enables signal generation without execution simulation
  - Useful for parameter tuning, signal validation, and debugging
  - Supports all direction modes (LONG, SHORT, BOTH)

- **Reproducibility Documentation** (T064)
  - Enhanced `specs/001-trend-pullback/quickstart.md` with reproducibility section
  - Documented hash computation algorithm and verification process
  - Added best practices for deterministic backtesting
  - Included storage locations and audit trail guidance

- **Jupyter Notebook Example** (T065)
  - Added `examples/long_signal_walkthrough.ipynb`
  - Demonstrates end-to-end strategy workflow with synthetic data
  - Includes trend classification, pullback detection, signal generation
  - Shows position sizing and risk management calculations
  - Educational resource for understanding strategy mechanics

### Added - Phase 5: User Story US3 (2025-10-28)

- **Full Metrics Calculations** (T045)
  - Enhanced `src/backtest/metrics.py` with expectancy, Sharpe, profit factor
  - Added win/loss ratio and average R-multiple computations
  - Handles zero-trade edge cases gracefully

- **Drawdown Analysis** (T046)
  - Implemented `src/backtest/drawdown.py` with drawdown curve computation
  - Added maximum drawdown and recovery time calculations
  - Supports drawdown period identification and analysis

- **Volatility Regime Classification** (T047)
  - Implemented `src/strategy/trend_pullback/volatility_regime.py`
  - Classifies market into LOW, NORMAL, HIGH, EXTREME volatility states
  - Detects volatility expansion and contraction events
  - Enables adaptive risk multipliers based on regime

- **Data Gap Handling** (T048)
  - Enhanced `src/io/ingestion.py` with timestamp gap detection
  - Warns on suspicious gaps that could indicate missing data
  - Maintains data integrity during streaming ingestion

- **Reproducibility Hash Finalization** (T049)
  - Completed `src/backtest/reproducibility.py` with hash verification
  - Implements deterministic SHA-256 hashing of backtest runs
  - Tracks parameters, data manifest, signals, and executions
  - Enables audit trail and result verification

- **CLI JSON Output** (T050)
  - Enhanced `src/cli/run_backtest.py` with `--output-format json`
  - Supports machine-readable backtest results
  - Enables programmatic analysis and automation

- **Error Path Testing** (T051-T052)
  - Added integration tests for manifest errors and zero-trade scenarios
  - Validates graceful error handling and edge case coverage

- **Performance Testing** (T053-T054)
  - Added throughput and memory usage measurement tests
  - Validates performance targets (50k+ candles/sec, ≤150MB memory)

### Added - Phase 4: User Story US2 (2025-10-27)

- **Short Signal Generation** (T039)
  - Extended `src/strategy/trend_pullback/signal_generator.py` with short logic
  - Mirrors long signal logic for bearish market conditions
  - Supports downtrend detection with pullback reversals

- **Short-Specific Testing** (T040-T042)
  - Added bearish reversal pattern tests
  - Validated short stop direction (above entry price)
  - Integration tests for short signal acceptance scenarios

- **Signal Cooldown** (T043)
  - Implemented cooldown period between signals (FR-019)
  - Prevents over-trading and signal clustering
  - Unit tests for cooldown enforcement

- **Direction Mode Toggle** (T044)
  - Enhanced CLI with `--direction` flag (LONG|SHORT|BOTH)
  - Supports mode-specific backtesting workflows

### Added - Phase 3: User Story US1 (2025-10-26)

- **Trend Classification** (T026)
  - Implemented `src/strategy/trend_pullback/trend_classifier.py`
  - EMA-based trend detection with ranging market filter
  - Returns TrendState (UP, DOWN, RANGE) with EMA and ATR values

- **Pullback Detection** (T027)
  - Implemented `src/strategy/trend_pullback/pullback_detector.py`
  - Detects counter-trend retracements with depth and age tracking
  - Validates pullback within ATR bounds

- **Reversal Pattern Recognition** (T028)
  - Implemented `src/strategy/trend_pullback/reversal.py`
  - Detects hammer and engulfing candlestick patterns
  - Includes momentum turn confirmation with RSI
  - Enforces pullback expiry timeout (FR-021: PULLBACK_MAX_AGE)

- **Long Signal Generator** (T029)
  - Implemented long signal generation in `src/strategy/trend_pullback/signal_generator.py`
  - Orchestrates trend, pullback, and reversal checks
  - Generates deterministic signal IDs

- **Risk Manager** (T030)
  - Implemented `src/risk/manager.py` with ATR-based stops
  - Position sizing with account equity percentage
  - Validates position size bounds (min/max constraints)

- **Execution Simulator** (T031)
  - Implemented `src/backtest/execution.py` with entry/exit logic
  - Supports fixed R-multiple targets and trailing stops
  - Enforces exit mode precedence (FR-026: target → trailing → stop → expiry)
  - Simulates realistic fill prices with gap handling

- **Metrics Ingestion** (T032)
  - Implemented `src/backtest/metrics_ingest.py` for streaming metrics
  - Accumulates trade executions in real-time
  - Supports zero-trade and partial execution scenarios

- **Observability Reporter** (T033)
  - Implemented `src/backtest/observability.py`
  - Structured logging for backtest events (start, signal, execution, error, finish)
  - Emits metrics summaries and reproducibility hashes

- **CLI Long Backtest** (T034)
  - Implemented `src/cli/run_long_backtest.py`
  - Command-line interface for long-signal-only backtests
  - Accepts CSV data path and manifest YAML
  - Outputs human-readable metrics to console

- **Integration & Unit Testing** (T035-T038)
  - Added acceptance tests for US1 scenarios
  - Unit tests for reversal patterns, risk sizing, cooldown
  - Performance test harness for throughput validation

### Added - Phase 2: Foundational (2025-10-25)

- **Core Data Models** (T011)
  - Implemented `src/models/core.py` with complete dataclass definitions
  - Candle, TrendState, PullbackState, TradeSignal, TradeExecution
  - BacktestRun, DataManifest, MetricsSummary
  - All models use Pydantic validation and type hints

- **Basic Indicators** (T012)
  - Implemented `src/indicators/basic.py` with EMA, ATR, RSI
  - Pure Python implementations for portability
  - Vectorized operations using list comprehensions

- **Data Ingestion** (T013)
  - Implemented `src/io/ingestion.py` with streaming CSV ingestion
  - Iterator-based candle yielding for memory efficiency
  - Timestamp gap detection and validation
  - Indicator computation during ingestion

- **Manifest Handling** (T014)
  - Implemented `src/io/manifest.py` for data provenance
  - YAML-based manifest loading and validation
  - SHA-256 checksum verification
  - Data lineage tracking for reproducibility

- **Signal ID Factory** (T015)
  - Implemented deterministic signal ID generation
  - SHA-256 hashing of currency pair, timestamp, and parameters
  - Truncated to 16-character hex for readability

- **Reproducibility Service** (T016)
  - Implemented `src/backtest/reproducibility.py` skeleton
  - Hash accumulator for parameters, data, signals, executions
  - Manifest reference tracking

- **Metrics Aggregator** (T017)
  - Implemented `src/backtest/metrics.py` skeleton
  - Basic metrics: trade count, win/loss count
  - Handles zero-trade scenarios

- **Latency Sampling** (T018)
  - Implemented `src/backtest/latency.py`
  - P95 and mean latency computation from samples
  - Supports performance profiling

- **Logging Setup** (T019)
  - Implemented `src/cli/logging_setup.py`
  - Structured JSON logging with configurable levels
  - Rich console formatting for human-readable output

- **Exception Definitions** (T020)
  - Implemented `src/models/exceptions.py`
  - DataIntegrityError, RiskLimitError, ExecutionSimulationError
  - Custom exceptions for domain-specific errors

- **Unit Testing** (T021-T025)
  - Comprehensive test coverage for indicators, manifest, ID factory
  - Reproducibility hash stability tests
  - Metrics aggregator zero-trade validation

### Added - Phase 1: Setup (2025-10-24)

- **Project Structure** (T001-T002)
  - Created complete source directory structure
  - Initialized Python packages with `__init__.py` files
  - Organized modules by domain: indicators, strategy, risk, backtest, io, cli

- **Dependency Management** (T003)
  - Added `pyproject.toml` with Poetry configuration
  - Specified Python 3.11 requirement
  - Declared dependencies: numpy, pandas, pydantic, rich, pytest, hypothesis

- **Version Control** (T004)
  - Added `.gitignore` for Python artifacts
  - Excluded `.venv/`, `__pycache__/`, build directories
  - Excluded data cache (`/data/raw/`) and backtest outputs (`/runs/`)

- **Configuration** (T005)
  - Implemented `src/config/parameters.py` with Pydantic settings
  - Strategy parameters with validation and defaults
  - Type-safe configuration management

- **Documentation** (T006)
  - Created `README.md` referencing quickstart guide
  - Project overview and feature highlights
  - Installation and development instructions

- **Test Infrastructure** (T007-T010)
  - Created `tests/conftest.py` with global pytest fixtures
  - Generated synthetic test datasets for US1, US2, US3
  - CSV fixtures: `sample_candles_long.csv`, `sample_candles_short.csv`, `sample_candles_empty.csv`

### Fixed

- **Lazy Logging** (2025-10-29)
  - Converted 62 logging calls from f-strings to lazy % formatting
  - Eliminated all W1203 (logging-fstring-interpolation) warnings
  - Improved pylint score from 8.78/10 to 9.68/10
  - Affects 16 files across backtest, cli, io, risk, and strategy modules

## [0.1.0] - Initial Release

### Context

This project implements a trend pullback continuation strategy for FX markets following constitutional principles:

- Strategy-first architecture (Principle I)
- Integrated risk management (Principle II)
- Real-time performance monitoring (Principle III)
- Data integrity and provenance (Principle V)
- Model parsimony (Principle VII)
- Code quality standards (Principle VIII, X)
- Dependency reproducibility (Principle IX)

See `.specify/memory/constitution.md` for full governance framework.

---

**Branch**: `001-trend-pullback`
**Spec**: `specs/001-trend-pullback/spec.md`
**Constitution**: v1.4.0 (ratified 2025-10-25, amended 2025-10-29)
