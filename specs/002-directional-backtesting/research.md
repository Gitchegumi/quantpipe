# Research: Directional Backtesting System

**Feature**: 002-directional-backtesting
**Date**: 2025-10-29
**Purpose**: Resolve technical unknowns and document architectural decisions

## Overview

This document consolidates research findings for implementing the unified directional backtesting CLI. All technical context items were resolved through analysis of existing codebase and industry best practices.

## Key Decisions

### Decision 1: CLI Orchestration Pattern

**Question**: How should the unified CLI orchestrate different direction modes while maintaining code reusability?

**Chosen Approach**: Factory/Strategy pattern with dedicated orchestrator module

**Rationale**:

- Separates CLI argument parsing from execution logic
- Enables easy testing of orchestration logic independently from CLI
- Supports future extension (e.g., adding NEUTRAL or custom direction modes)
- Existing codebase already uses similar separation (`run_long_backtest.py` delegates to signal generator)

**Implementation Pattern**:

```python
class BacktestOrchestrator:
    def run_backtest(
        self,
        direction: DirectionMode,
        candles: Sequence[Candle],
        config: BacktestConfig
    ) -> BacktestResult:
        # Route based on direction
        # Aggregate metrics
        # Return unified result
```

**Alternatives Considered**:

- **Monolithic CLI with if/elif blocks**: Rejected - poor testability, difficult to maintain
- **Separate executables per direction**: Rejected - code duplication, inconsistent UX

---

### Decision 2: BOTH Mode Conflict Resolution Architecture

**Question**: How should simultaneous long/short signals be detected and resolved efficiently?

**Chosen Approach**: Timestamp-based merge with conflict detection during signal generation phase

**Rationale**:

- Clarification Q1 established: reject both signals when timestamps identical (choppy market indicator)
- Early detection prevents unnecessary execution simulation overhead
- Maintains signal generation as pure functions (no side effects)
- Logging confined to orchestrator layer

**Implementation Pattern**:

```python
def merge_signals(
    long_signals: list[TradeSignal],
    short_signals: list[TradeSignal]
) -> tuple[list[TradeSignal], list[ConflictEvent]]:
    # Group by timestamp
    # Detect conflicts (same timestamp, same pair)
    # Apply resolution logic per clarifications
    # Return merged signal list + conflict log
```

**Alternatives Considered**:

- **Post-execution conflict handling**: Rejected - wastes computation on signals that will be rejected
- **Priority-based resolution (long always wins)**: Rejected - user clarification specified rejection approach

---

### Decision 3: Metrics Aggregation for BOTH Mode

**Question**: How should separate long/short metrics be calculated and combined?

**Chosen Approach**: Three-tier metrics calculation (long-only, short-only, combined)

**Rationale**:

- Clarification Q5 established: aggregate all trades together for combined metrics
- Enables comparative analysis between directional performance
- Simple filtering by trade direction attribute
- Follows existing metrics calculation patterns

**Implementation Pattern**:

```python
class DirectionalMetrics:
    long_only: MetricsSummary   # Filter trades where direction == "LONG"
    short_only: MetricsSummary  # Filter trades where direction == "SHORT"
    combined: MetricsSummary    # All trades aggregated
```

**Alternatives Considered**:

- **Weighted averaging**: Rejected - clarification specified direct aggregation
- **Separate-only reporting**: Rejected - combined metrics required per FR-022

---

### Decision 4: Output File Naming and Management

**Question**: How should output files be named to prevent overwrites and enable organization?

**Chosen Approach**: Deterministic timestamp-based naming per clarification Q2

**Rationale**:

- Format: `backtest_{direction}_{YYYYMMDD}_{HHMMSS}.{ext}`
- Direction in filename enables filtering (e.g., `ls backtest_long_*`)
- Chronological sorting via timestamp
- Extension flexibility (txt/json)

**Implementation Pattern**:

```python
def generate_output_filename(
    direction: DirectionMode,
    output_format: OutputFormat,
    timestamp: datetime
) -> str:
    direction_str = direction.lower()  # long/short/both
    date_str = timestamp.strftime("%Y%m%d")
    time_str = timestamp.strftime("%H%M%S")
    ext = "json" if output_format == "json" else "txt"
    return f"backtest_{direction_str}_{date_str}_{time_str}.{ext}"
```

**Alternatives Considered**:

- **UUID-based names**: Rejected - not human-readable, no sorting benefit
- **Counter-based names**: Rejected - not robust to concurrent runs

---

### Decision 5: JSON Output Schema Design

**Question**: What schema should JSON output follow for consistency and extensibility?

**Chosen Approach**: Nested structure with run metadata, metrics, and optional details

**Rationale**:

- Separates concerns (metadata vs. results vs. diagnostics)
- ISO 8601 UTC for all timestamps (FR-023)
- NaN/Infinity serialization as null or string (FR-024)
- Pydantic models ensure type safety and validation

**Schema Structure**:

```json
{
  "run_metadata": {
    "run_id": "string",
    "direction": "LONG|SHORT|BOTH",
    "parameters_hash": "string",
    "manifest_ref": "string",
    "start_time": "ISO 8601 UTC",
    "end_time": "ISO 8601 UTC",
    "total_candles_processed": 0,
    "reproducibility_hash": "string"
  },
  "metrics": {
    "combined": {
      /* MetricsSummary */
    },
    "long_only": {
      /* MetricsSummary or null */
    },
    "short_only": {
      /* MetricsSummary or null */
    }
  },
  "signals": [
    /* optional, for dry-run mode */
  ],
  "executions": [
    /* optional, for full detail */
  ],
  "conflicts": [
    /* for BOTH mode */
  ]
}
```

**Alternatives Considered**:

- **Flat structure**: Rejected - difficult to extend, namespace pollution
- **CSV-like array output**: Rejected - loses hierarchical relationships

---

### Decision 6: Dry-Run Mode Implementation

**Question**: How should dry-run mode minimize overhead while providing useful signal validation?

**Chosen Approach**: Signal generation only, skip execution simulation entirely

**Rationale**:

- Clarification Q4 established essential output fields: timestamp, pair, direction, entry_price, stop_price
- Skip `simulate_execution` calls entirely (FR-021)
- 10-second target for 100K candles achievable by avoiding candle iteration
- Output focuses on signal frequency and parameter inspection

**Implementation Pattern**:

```python
if dry_run:
    signals = generate_signals(candles, direction)
    output_signal_list(signals, essential_fields_only=True)
else:
    signals = generate_signals(candles, direction)
    executions = [simulate_execution(s, candles) for s in signals]
    output_full_results(executions)
```

**Alternatives Considered**:

- **Fast execution mode**: Rejected - still requires candle iteration, doesn't meet 10s target
- **Sampling approach**: Rejected - user needs complete signal set for validation

---

## Technology Stack Confirmation

### Existing Dependencies (No Changes Required)

- **Python 3.11**: Current project version
- **numpy**: Array operations for candle data
- **pandas**: Time series handling (existing in signal generation)
- **pydantic**: Data validation for models (BacktestRun, MetricsSummary)
- **rich**: Structured logging (existing)
- **pytest + hypothesis**: Testing framework (existing)

### Standard Library Usage

- **argparse**: CLI argument parsing (existing pattern in run_long_backtest.py)
- **json**: JSON serialization for output format
- **pathlib**: Path handling for file operations
- **datetime**: Timestamp handling (UTC enforcement)
- **typing**: Type hints for all signatures

**Decision**: No new external dependencies required. Feature builds entirely on existing stack.

---

## Best Practices Applied

### CLI Design Patterns

1. **Argument Validation**: Fail fast with clear error messages (FR-017)
2. **Default Values**: Sensible defaults for optional arguments (--output-format text)
3. **Help Text**: Comprehensive --help output with examples
4. **Exit Codes**: 0 for success, 1 for errors, consistent with Unix conventions

### Logging Strategy

1. **Lazy % Formatting**: Per Constitution Principle X (`logger.info("Processing %d items", count)`)
2. **Structured Levels**: DEBUG for signals, INFO for progress, WARNING for conflicts, ERROR for failures
3. **Configurable Verbosity**: --log-level flag (FR-019)
4. **Conflict Logging**: Timestamp + pair only per clarification Q3

### Error Handling

1. **Input Validation**: Check file existence before processing (FR-017)
2. **Graceful Degradation**: Handle incomplete trades, log warnings, continue (edge case handling)
3. **Clear Error Messages**: User-actionable error descriptions

### Testing Strategy

1. **Unit Tests**: Orchestrator logic, metrics aggregation, formatters
2. **Integration Tests**: End-to-end CLI with fixture data
3. **Property-Based Tests**: Use hypothesis for edge cases (empty signals, conflicting timestamps)
4. **Determinism Verification**: Assert reproducibility_hash consistency across reruns

---

## Performance Considerations

### Target Achievement Strategy

| Target               | Approach                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------ |
| 100K candles in ≤30s | Leverage existing optimized signal generation; use generator patterns for large datasets   |
| Dry-run in ≤10s      | Skip execution simulation; output only essential signal fields                             |
| JSON ≤10MB for 100K  | Exclude verbose fields in default output; provide --verbose flag for full detail if needed |

### Optimization Techniques

1. **Generator Functions**: Stream candles rather than loading all into memory
2. **Minimal Serialization**: Only include necessary fields in JSON output
3. **Batch Processing**: Group operations to reduce overhead
4. **Avoid Redundant Calculations**: Cache common values (e.g., parameters_hash)

---

## Risk Mitigation

### Identified Risks

1. **Risk**: BOTH mode performance degradation due to signal merging overhead

   - **Mitigation**: Use hash-based grouping (O(n) complexity); benchmark against targets

2. **Risk**: JSON serialization of NaN/Infinity causes parsing errors

   - **Mitigation**: Explicit handling per FR-024; test with edge case datasets

3. **Risk**: File naming collisions in rapid sequential runs

   - **Mitigation**: Second-precision timestamps sufficient for typical usage; document limitation

4. **Risk**: Memory usage with large datasets (>1M candles)
   - **Mitigation**: Generator patterns; document recommended dataset size limits

---

## Open Questions (Deferred to Implementation)

None - all critical decisions resolved through codebase analysis and clarification session.

---

## References

- Existing codebase patterns: `src/cli/run_long_backtest.py`, `src/backtest/execution.py`
- Constitution principles: v1.4.0 (Principles VIII, IX, X)
- Clarification session: 2025-10-29 (5 questions resolved)
- Python best practices: PEP 8, PEP 257, Python 3.11 type hints
