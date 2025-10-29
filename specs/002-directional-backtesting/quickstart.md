# Quickstart: Directional Backtesting System

**Feature**: 002-directional-backtesting
**Date**: 2025-10-29
**For**: Developers implementing this feature

## Overview

This guide provides step-by-step instructions for implementing the directional backtesting system. Follow these phases in order for systematic development.

## Prerequisites

- Python 3.11+ installed
- Poetry package manager configured
- Repository cloned and dependencies installed (`poetry install`)
- Familiarity with existing codebase:
  - `src/cli/run_long_backtest.py` (existing LONG implementation)
  - `src/backtest/execution.py` (simulate_execution function)
  - `src/strategy/trend_pullback/signal_generator.py` (signal generation)
  - `src/models/core.py` (data models)

## Development Phases

### Phase 1: Core Data Models (Est: 2 hours)

**Goal**: Add new Pydantic models to `src/models/core.py`

**Tasks**:

1. Add `DirectionMode` enum:

   ```python
   from enum import Enum

   class DirectionMode(str, Enum):
       LONG = "LONG"
       SHORT = "SHORT"
       BOTH = "BOTH"
   ```

2. Add `OutputFormat` enum:

   ```python
   class OutputFormat(str, Enum):
       TEXT = "text"
       JSON = "json"
   ```

3. Add `ConflictEvent` model:

   ```python
   class ConflictEvent(BaseModel):
       timestamp_utc: datetime
       pair: str
       resolution: str = "REJECTED_BOTH"
   ```

4. Add `DirectionalMetrics` model:

   ```python
   class DirectionalMetrics(BaseModel):
       long_only: Optional[MetricsSummary] = None
       short_only: Optional[MetricsSummary] = None
       combined: MetricsSummary
   ```

5. Add `BacktestResult` model:

   ```python
   class BacktestResult(BaseModel):
       run_metadata: BacktestRun
       metrics: DirectionalMetrics
       signals: list[TradeSignal] = []
       executions: list[TradeExecution] = []
       conflicts: list[ConflictEvent] = []
   ```

**Validation**:

- Run `poetry run pytest tests/unit/test_models.py` (add tests for new models)
- Check type hints with `poetry run mypy src/models/core.py`

---

### Phase 2: Backtest Orchestrator (Est: 4 hours)

**Goal**: Create `src/backtest/orchestrator.py` with core logic

**Tasks**:

1. Create orchestrator module with main class:

   ```python
   class BacktestOrchestrator:
       def run_backtest(
           self,
           direction: DirectionMode,
           candles: Sequence[Candle],
           dry_run: bool = False
       ) -> BacktestResult:
           # Implementation
   ```

2. Implement direction routing:

   - LONG: call `generate_long_signals(candles)`
   - SHORT: call `generate_short_signals(candles)`
   - BOTH: call both + merge with conflict resolution

3. Implement `merge_signals` function:

   ```python
   def merge_signals(
       long_signals: list[TradeSignal],
       short_signals: list[TradeSignal]
   ) -> tuple[list[TradeSignal], list[ConflictEvent]]:
       # Group by timestamp + pair
       # Detect conflicts (identical timestamp)
       # Reject both signals per clarification Q1
       # Return merged list + conflicts
   ```

4. Implement execution logic:

   - If dry_run: skip execution, return signals only
   - Else: call `simulate_execution` for each signal

5. Implement metrics aggregation (delegate to Phase 3)

**Validation**:

- Write unit tests in `tests/unit/test_backtest_orchestrator.py`
- Test conflict detection with manufactured signals
- Verify dry-run skips execution

---

### Phase 3: Metrics Aggregation (Est: 3 hours)

**Goal**: Create/enhance `src/backtest/metrics.py`

**Tasks**:

1. Create `calculate_metrics` function:

   ```python
   def calculate_metrics(
       executions: list[TradeExecution]
   ) -> MetricsSummary:
       # Existing metrics calculation logic
       # Or call existing function if available
   ```

2. Create `calculate_directional_metrics` function:

   ```python
   def calculate_directional_metrics(
       executions: list[TradeExecution],
       direction: DirectionMode
   ) -> DirectionalMetrics:
       if direction == DirectionMode.LONG:
           combined = calculate_metrics(executions)
           return DirectionalMetrics(long_only=combined, combined=combined)
       elif direction == DirectionMode.SHORT:
           combined = calculate_metrics(executions)
           return DirectionalMetrics(short_only=combined, combined=combined)
       else:  # BOTH
           long_execs = [e for e in executions if e.direction == "LONG"]
           short_execs = [e for e in executions if e.direction == "SHORT"]
           return DirectionalMetrics(
               long_only=calculate_metrics(long_execs),
               short_only=calculate_metrics(short_execs),
               combined=calculate_metrics(executions)
           )
   ```

**Validation**:

- Write tests in `tests/unit/test_metrics_aggregation.py`
- Test with empty executions (handle NaN cases)
- Verify three-tier metrics for BOTH mode

---

### Phase 4: Output Formatters (Est: 3 hours)

**Goal**: Create `src/io/formatters.py` for text/JSON output

**Tasks**:

1. Create `format_text_output` function:

   ```python
   def format_text_output(result: BacktestResult) -> str:
       # Human-readable format
       # Include run metadata
       # Include metrics summary
       # Include directional breakdown for BOTH mode
       # Include conflicts if any
   ```

2. Create `format_json_output` function:

   ```python
   def format_json_output(result: BacktestResult) -> str:
       # Serialize to JSON per schema
       # Handle NaN/Infinity (convert to null or string)
       # ISO 8601 UTC for all datetimes
       # Validate against json-output-schema.json
   ```

3. Create `generate_output_filename` function:

   ```python
   def generate_output_filename(
       direction: DirectionMode,
       output_format: OutputFormat,
       timestamp: datetime
   ) -> str:
       direction_str = direction.value.lower()
       date_str = timestamp.strftime("%Y%m%d")
       time_str = timestamp.strftime("%H%M%S")
       ext = "json" if output_format == OutputFormat.JSON else "txt"
       return f"backtest_{direction_str}_{date_str}_{time_str}.{ext}"
   ```

**Validation**:

- Write tests in `tests/unit/test_output_formatters.py`
- Validate JSON against schema
- Test filename generation with various inputs

---

### Phase 5: CLI Enhancement (Est: 2 hours)

**Goal**: Enhance `src/cli/run_backtest.py` with unified interface

**Tasks**:

1. Update argument parser to match contracts/cli-interface.md

2. Replace placeholder logic with orchestrator calls:

   ```python
   from src.backtest.orchestrator import BacktestOrchestrator
   from src.io import formatters

   orchestrator = BacktestOrchestrator()
   result = orchestrator.run_backtest(
       direction=args.direction,
       candles=candles,
       dry_run=args.dry_run
   )
   ```

3. Add output file handling:

   ```python
   filename = formatters.generate_output_filename(
       direction=args.direction,
       output_format=args.output_format,
       timestamp=datetime.now(UTC)
   )
   output_path = args.output / filename

   if args.output_format == OutputFormat.JSON:
       content = formatters.format_json_output(result)
   else:
       content = formatters.format_text_output(result)

   output_path.write_text(content)
   ```

4. Add logging calls (lazy % formatting per Constitution Principle X):

   ```python
   logger.info("Generating %s signals...", args.direction)
   logger.info("Generated %d signals", len(signals))
   logger.warning("Conflict detected: timestamp=%s, pair=%s", ts, pair)
   ```

**Validation**:

- Manual testing with sample data
- Verify all CLI arguments work
- Check output file naming
- Verify logging follows lazy % format

---

### Phase 6: Integration Tests (Est: 3 hours)

**Goal**: Create end-to-end tests in `tests/integration/test_directional_backtesting.py`

**Tasks**:

1. Test LONG mode:

   - Load fixture data
   - Run backtest
   - Verify output file created
   - Validate metrics structure

2. Test SHORT mode:

   - Same as LONG with SHORT direction

3. Test BOTH mode:

   - Create fixture with conflicting signals
   - Verify conflict resolution
   - Validate three-tier metrics

4. Test dry-run mode:

   - Verify no executions
   - Validate signal output

5. Test JSON output:
   - Validate against schema
   - Check datetime formatting
   - Verify NaN handling

**Validation**:

- `poetry run pytest tests/integration/test_directional_backtesting.py`
- Aim for 100% test coverage on new modules

---

### Phase 7: Code Quality & Documentation (Est: 2 hours)

**Goal**: Ensure code meets constitution standards

**Tasks**:

1. Format code:

   ```bash
   poetry run black src/ tests/
   ```

2. Run Ruff linter:

   ```bash
   poetry run ruff check src/ tests/
   ```

   - Fix all errors (zero errors required)

3. Run Pylint:

   ```bash
   poetry run pylint src/backtest/ src/io/ src/cli/run_backtest.py --score=yes
   ```

   - Achieve ≥8.0/10 score
   - Fix all W1203 (logging-fstring-interpolation) warnings

4. Add docstrings (PEP 257):

   - All modules
   - All classes
   - All functions
   - Include examples in docstrings

5. Add type hints:
   - All function signatures
   - All class attributes
   - Run `poetry run mypy src/` to verify

**Validation**:

- All quality checks pass
- No linting errors or warnings (except score <8.0)

---

### Phase 8: Performance Validation (Est: 1 hour)

**Goal**: Verify performance targets met

**Tasks**:

1. Benchmark LONG mode with 100K candles:

   ```bash
   time poetry run python -m src.cli.run_backtest \
     --direction LONG \
     --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv
   ```

   - Target: ≤30 seconds

2. Benchmark dry-run mode:

   ```bash
   time poetry run python -m src.cli.run_backtest \
     --direction LONG \
     --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv \
     --dry-run
   ```

   - Target: ≤10 seconds

3. Check JSON output size:

   ```bash
   poetry run python -m src.cli.run_backtest \
     --direction BOTH \
     --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv \
     --output-format json
   ls -lh results/backtest_both_*.json
   ```

   - Target: ≤10 MB

**Validation**:

- All performance targets met
- Document actual timings

---

## Testing Checklist

Before considering implementation complete:

- [ ] All unit tests pass (`poetry run pytest tests/unit/`)
- [ ] All integration tests pass (`poetry run pytest tests/integration/`)
- [ ] Code formatted with Black (`poetry run black src/ tests/`)
- [ ] Ruff linter passes with zero errors (`poetry run ruff check src/ tests/`)
- [ ] Pylint score ≥8.0/10 (`poetry run pylint src/backtest/ src/io/ src/cli/run_backtest.py --score=yes`)
- [ ] All W1203 logging warnings fixed (lazy % formatting)
- [ ] Type hints complete (`poetry run mypy src/`)
- [ ] Docstrings added to all modules/classes/functions (PEP 257)
- [ ] Performance targets met (see Phase 8)
- [ ] JSON output validates against schema
- [ ] Manual smoke testing completed
- [ ] Constitution check passes (see plan.md)

---

## Common Pitfalls & Solutions

### Pitfall 1: F-strings in Logging

**Problem**: Using f-strings in logging calls triggers W1203

**Solution**: Use lazy % formatting

```python
# ❌ Wrong
logger.info(f"Processing {count} items")

# ✅ Correct
logger.info("Processing %d items", count)
```

---

### Pitfall 2: NaN Serialization in JSON

**Problem**: `json.dumps()` fails with NaN/Infinity values

**Solution**: Custom JSON encoder or pre-processing

```python
import math
import json

def serialize_metrics(metrics: MetricsSummary) -> dict:
    data = metrics.dict()
    for key, value in data.items():
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            data[key] = None  # or str(value)
    return data
```

---

### Pitfall 3: Timestamp Timezone Issues

**Problem**: Datetime objects without timezone info

**Solution**: Always use UTC with timezone

```python
from datetime import datetime, UTC

# ✅ Correct
now = datetime.now(UTC)

# ❌ Wrong
now = datetime.now()
```

---

### Pitfall 4: Conflict Detection Edge Cases

**Problem**: Missing conflicts due to floating-point timestamp comparison

**Solution**: Group by timestamp string or use timestamp truncation

```python
# Group by timestamp (already datetime objects, use direct equality)
from collections import defaultdict

signals_by_ts_pair = defaultdict(list)
for sig in all_signals:
    key = (sig.timestamp_utc, sig.pair)
    signals_by_ts_pair[key].append(sig)

# Detect conflicts
for (ts, pair), sigs in signals_by_ts_pair.items():
    if len(sigs) > 1:
        # Check if different directions
        directions = {s.direction for s in sigs}
        if len(directions) > 1:
            # Conflict! Reject both
            conflicts.append(ConflictEvent(timestamp_utc=ts, pair=pair))
```

---

## File Modification Summary

| File                                                | Action | Description                        |
| --------------------------------------------------- | ------ | ---------------------------------- |
| `src/models/core.py`                                | EDIT   | Add new Pydantic models            |
| `src/backtest/orchestrator.py`                      | CREATE | Backtest orchestration logic       |
| `src/backtest/metrics.py`                           | CREATE | Metrics aggregation functions      |
| `src/io/formatters.py`                              | CREATE | Text/JSON output formatters        |
| `src/cli/run_backtest.py`                           | EDIT   | Enhance CLI with unified interface |
| `tests/unit/test_backtest_orchestrator.py`          | CREATE | Orchestrator unit tests            |
| `tests/unit/test_metrics_aggregation.py`            | CREATE | Metrics unit tests                 |
| `tests/unit/test_output_formatters.py`              | CREATE | Formatter unit tests               |
| `tests/integration/test_directional_backtesting.py` | CREATE | End-to-end tests                   |

**Estimated Total Time**: 20 hours (2.5 days)

---

## Resources

- **Specification**: [spec.md](./spec.md)
- **Research**: [research.md](./research.md)
- **Data Model**: [data-model.md](./data-model.md)
- **CLI Contract**: [contracts/cli-interface.md](./contracts/cli-interface.md)
- **JSON Schema**: [contracts/json-output-schema.json](./contracts/json-output-schema.json)
- **Constitution**: `.specify/memory/constitution.md`
- **Existing Code**: `src/cli/run_long_backtest.py`, `src/backtest/execution.py`

---

## Getting Help

If you encounter issues:

1. Check existing codebase for similar patterns
2. Review clarification session in spec.md (5 Q&A pairs)
3. Validate against constitution principles
4. Run tests frequently to catch issues early
5. Use type hints and mypy to catch type errors before runtime

Good luck! 🚀
