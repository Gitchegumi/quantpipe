# Research: Multi-Timeframe Backtesting

## Technical Context Resolution

### Decision 1: Resampling Library

**Decision**: Use Polars `group_by_dynamic()` for OHLCV resampling
**Rationale**:

- Project already uses Polars extensively (`ingestion.py` supports `return_polars=True`)
- Polars `group_by_dynamic()` provides native time-based grouping with truncation
- Significantly faster than pandas `.resample()` on large datasets (6.9M rows)
- Maintains consistency with existing vectorized backtest path

**Alternatives Considered**:

- pandas `.resample()`: Slower, requires conversion between Polars/Pandas
- Manual grouping: More complex, error-prone

### Decision 2: Resampling Integration Point

**Decision**: Create new `src/data_io/resample.py` module with `resample_ohlcv()` function
**Rationale**:

- Separates concerns from ingestion (ingestion = load, resample = transform)
- Called after ingestion, before indicator computation
- Can be cached independently of raw data cache
- Allows future use cases (e.g., pre-resample for optimization sweeps)

**Alternatives Considered**:

- Add to `ingestion.py`: Would bloat already complex module (676 lines)
- Add to orchestrator: Mixing data transformation with backtest execution

### Decision 3: Timeframe Parser Location

**Decision**: Create `src/data_io/timeframe.py` with `parse_timeframe()` and `Timeframe` dataclass
**Rationale**:

- Reusable across CLI, API, and config validation
- Follows existing pattern (`src/data_io/schema.py` for schema validation)
- Single source of truth for timeframe parsing

### Decision 4: Cache Storage Format

**Decision**: Parquet files in `.time_cache/` with filename pattern `{instrument}_{tf}_{start}_{end}_{hash}.parquet`
**Rationale**:

- Parquet provides fast I/O and good compression
- Pattern matches existing `parquet_cache.py` approach
- Hash includes data version for invalidation

### Decision 5: CLI Integration

**Decision**: Add `--timeframe` argument to `argparse` in `run_backtest.py`
**Rationale**:

- Follows existing CLI pattern (already has `--pair`, `--direction`, etc.)
- Default to `1m` for backward compatibility

## Dependencies

- Polars (already installed)
- No new dependencies required

## Patterns Applied

- Dataclass for `Timeframe` entity (matches `IngestionResult`, `IngestionMetrics`)
- Functional composition: `ingest() → resample() → compute_indicators() → backtest()`
- Cache pattern from `parquet_cache.py`
