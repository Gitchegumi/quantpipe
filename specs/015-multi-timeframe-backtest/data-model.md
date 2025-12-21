# Data Model: Multi-Timeframe Backtesting

## Entities

### Timeframe

Represents a valid backtesting timeframe parsed from user input.

| Field            | Type   | Description                                  |
| ---------------- | ------ | -------------------------------------------- |
| `period_minutes` | `int`  | Total period in minutes (e.g., 120 for "2h") |
| `original_input` | `str`  | Original user input (e.g., "2h")             |
| `is_valid`       | `bool` | Whether the timeframe is valid               |

**Validation Rules**:

- Format must match regex: `^(\d+)(m|h|d)$`
- Numeric value must be ≥ 1
- Resulting minutes must be ≥ 1

**Examples**:

- `"15m"` → `Timeframe(period_minutes=15, original_input="15m", is_valid=True)`
- `"2h"` → `Timeframe(period_minutes=120, original_input="2h", is_valid=True)`
- `"1d"` → `Timeframe(period_minutes=1440, original_input="1d", is_valid=True)`
- `"0m"` → raises `ValueError`

---

### ResampledBar

An OHLCV bar aggregated from constituent 1-minute bars.

| Field           | Type       | Description                             |
| --------------- | ---------- | --------------------------------------- |
| `timestamp_utc` | `datetime` | Bar close timestamp (UTC)               |
| `open`          | `float`    | First open price in period              |
| `high`          | `float`    | Maximum high price in period            |
| `low`           | `float`    | Minimum low price in period             |
| `close`         | `float`    | Last close price in period              |
| `volume`        | `float`    | Sum of volume in period                 |
| `bar_complete`  | `bool`     | True if all constituent minutes present |

**Aggregation Rules**:

- `open`: First value in group
- `high`: Maximum value in group
- `low`: Minimum value in group
- `close`: Last value in group
- `volume`: Sum of all values in group
- `bar_complete`: `count == expected_count`

---

### ResampleCache (Internal)

Disk-cached resampled data to avoid recomputation.

**Cache Key Components**:

| Component    | Source               | Example        |
| ------------ | -------------------- | -------------- |
| `instrument` | CLI/config           | `"EURUSD"`     |
| `timeframe`  | CLI/config           | `"15m"`        |
| `start_date` | Data bounds          | `"2023-01-01"` |
| `end_date`   | Data bounds          | `"2024-01-01"` |
| `data_hash`  | Computed from source | `"a1b2c3..."`  |

**Cache Path**: `.time_cache/{instrument}_{timeframe}_{start}_{end}_{hash8}.parquet`

---

## State Transitions

### Timeframe Parsing Flow

```text
User Input → parse_timeframe() → Timeframe (valid) or ValueError (invalid)
```

### Data Resampling Flow

```text
1-min DataFrame → resample_ohlcv(df, timeframe) → Resampled DataFrame
                                                  └─→ Cached to disk
```

### Backtest Data Flow (Updated)

```text
CSV/Parquet → ingest_ohlcv_data() → 1-min DataFrame
                                          │
                                          ▼
                                   resample_ohlcv() [if tf != 1m]
                                          │
                                          ▼
                                   Resampled DataFrame
                                          │
                                          ▼
                                compute_indicators() → Enriched DataFrame
                                          │
                                          ▼
                                   run_backtest() → BacktestResult
```
