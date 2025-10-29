# CLI Interface Contract

**Feature**: 002-directional-backtesting
**Command**: `run_backtest.py`
**Purpose**: Unified CLI for directional backtesting

## Command Synopsis

```bash
python -m src.cli.run_backtest [OPTIONS]
```

## Required Arguments

### `--data PATH`

**Type**: Path to CSV file
**Required**: Yes
**Description**: Path to historical price data file in CSV format

**Example**:

```bash
--data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv
```

**Validation**:

- File must exist
- File must be readable
- File must be valid CSV with required columns

**Error Behavior**:

- Exit code 1 if file not found
- Error message: "Error: Data file not found: {path}"

---

## Optional Arguments

### `--direction {LONG,SHORT,BOTH}`

**Type**: Choice
**Required**: No
**Default**: LONG
**Description**: Trading direction mode

**Values**:

- `LONG`: Generate and execute long-only signals
- `SHORT`: Generate and execute short-only signals
- `BOTH`: Generate both long and short signals with conflict resolution

**Example**:

```bash
--direction BOTH
```

**Validation**:

- Must be one of {LONG, SHORT, BOTH}
- Case-sensitive

---

### `--output PATH`

**Type**: Directory path
**Required**: No
**Default**: `results/`
**Description**: Output directory for backtest results

**Example**:

```bash
--output backtest_results/
```

**Validation**:

- Directory created if doesn't exist
- Must be writable

**Output File Naming**:

Format: `backtest_{direction}_{YYYYMMDD}_{HHMMSS}.{ext}`

- `{direction}`: lowercase (long/short/both)
- `{YYYYMMDD}`: Date (e.g., 20251029)
- `{HHMMSS}`: Time (e.g., 143052)
- `{ext}`: txt or json based on --output-format

Examples:

- `backtest_long_20251029_143052.txt`
- `backtest_both_20251029_150000.json`

---

### `--output-format {text,json}`

**Type**: Choice
**Required**: No
**Default**: text
**Description**: Output format for backtest results

**Values**:

- `text`: Human-readable text format
- `json`: Machine-readable JSON format (see json-output-schema.json)

**Example**:

```bash
--output-format json
```

**Validation**:

- Must be one of {text, json}
- Case-sensitive

---

### `--log-level {DEBUG,INFO,WARNING,ERROR}`

**Type**: Choice
**Required**: No
**Default**: INFO
**Description**: Logging verbosity level

**Values**:

- `DEBUG`: Detailed debugging information
- `INFO`: General informational messages
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

**Example**:

```bash
--log-level DEBUG
```

**Validation**:

- Must be one of {DEBUG, INFO, WARNING, ERROR}
- Case-sensitive

---

### `--dry-run`

**Type**: Flag
**Required**: No
**Default**: False
**Description**: Generate signals without executing them (signal-only mode)

**Example**:

```bash
--dry-run
```

**Behavior**:

- Generates signals according to --direction
- Skips execution simulation
- Outputs signal list with essential fields only
- Target: ≤10 seconds for 100K candles

**Output Fields** (dry-run mode):

- timestamp
- pair
- direction
- entry_price
- stop_price

---

## Exit Codes

| Code | Meaning | Scenarios |
|------|---------|-----------|
| 0 | Success | Backtest completed successfully |
| 1 | Error | Data file not found, invalid arguments, data parsing failure |

---

## Usage Examples

### Example 1: Basic LONG backtest

```bash
python -m src.cli.run_backtest --direction LONG --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv
```

**Output**: `results/backtest_long_20251029_143052.txt`

---

### Example 2: BOTH mode with JSON output

```bash
python -m src.cli.run_backtest \
  --direction BOTH \
  --data price_data/usdjpy/DAT_MT_USDJPY_M1_2021.csv \
  --output-format json \
  --output backtest_results/
```

**Output**: `backtest_results/backtest_both_20251029_143052.json`

---

### Example 3: Dry-run for signal validation

```bash
python -m src.cli.run_backtest \
  --direction SHORT \
  --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv \
  --dry-run \
  --log-level DEBUG
```

**Output**: Signal list (no execution), debug logging enabled

---

### Example 4: Custom output directory

```bash
python -m src.cli.run_backtest \
  --direction LONG \
  --data price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv \
  --output /path/to/custom/results/
```

**Output**: `/path/to/custom/results/backtest_long_20251029_143052.txt`

---

## Help Output

```bash
python -m src.cli.run_backtest --help
```

**Expected Output**:

```text
usage: run_backtest.py [-h] --data DATA [--direction {LONG,SHORT,BOTH}]
                       [--output OUTPUT] [--output-format {text,json}]
                       [--log-level {DEBUG,INFO,WARNING,ERROR}] [--dry-run]

Run trend-pullback backtest with configurable direction

required arguments:
  --data DATA           Path to CSV price data file

optional arguments:
  -h, --help            show this help message and exit
  --direction {LONG,SHORT,BOTH}
                        Trading direction: LONG (buy only), SHORT (sell only),
                        or BOTH (default: LONG)
  --output OUTPUT       Output directory for results (default: results/)
  --output-format {text,json}
                        Output format: text (human-readable) or json
                        (machine-readable) (default: text)
  --log-level {DEBUG,INFO,WARNING,ERROR}
                        Logging level (default: INFO)
  --dry-run             Generate signals without execution (signal-only mode)
```

---

## Error Messages

### Data File Not Found

```text
Error: Data file not found: price_data/missing.csv
```

**Exit Code**: 1

---

### Invalid Direction

```text
error: argument --direction: invalid choice: 'INVALID' (choose from 'LONG', 'SHORT', 'BOTH')
```

**Exit Code**: 1 (argparse handles this automatically)

---

### Invalid Output Format

```text
error: argument --output-format: invalid choice: 'xml' (choose from 'text', 'json')
```

**Exit Code**: 1 (argparse handles this automatically)

---

## Performance Guarantees

| Operation | Dataset Size | Target | Actual (Expected) |
|-----------|--------------|--------|-------------------|
| LONG backtest | 100K candles | ≤30s | ~20-25s |
| SHORT backtest | 100K candles | ≤30s | ~20-25s |
| BOTH backtest | 100K candles | ≤30s | ~25-30s |
| Dry-run (any) | 100K candles | ≤10s | ~5-8s |

---

## Logging Output Samples

### INFO Level (Default)

```text
2025-10-29 14:30:52 - INFO - Loading data from price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv
2025-10-29 14:30:53 - INFO - Loaded 105120 candles
2025-10-29 14:30:53 - INFO - Generating LONG signals...
2025-10-29 14:30:55 - INFO - Generated 42 signals
2025-10-29 14:30:55 - INFO - Simulating execution for 42 signals...
2025-10-29 14:31:05 - INFO - Completed 42 executions
2025-10-29 14:31:05 - INFO - Calculating metrics...
2025-10-29 14:31:05 - INFO - Backtest complete: 42 trades, 60% win rate, avg R: 1.24
2025-10-29 14:31:05 - INFO - Results saved to results/backtest_long_20251029_143052.txt
```

---

### DEBUG Level

```text
2025-10-29 14:30:52 - DEBUG - Parsing CLI arguments
2025-10-29 14:30:52 - DEBUG - Direction: LONG, Output format: text
2025-10-29 14:30:52 - INFO - Loading data from price_data/eurusd/DAT_MT_EURUSD_M1_2020.csv
2025-10-29 14:30:53 - DEBUG - Data ingestion complete: 105120 rows
2025-10-29 14:30:53 - INFO - Loaded 105120 candles
2025-10-29 14:30:53 - INFO - Generating LONG signals...
2025-10-29 14:30:54 - DEBUG - Signal generated: id=a1b2c3d4e5f6g7h8, timestamp=2020-01-15 10:30:00, entry=1.1145
2025-10-29 14:30:54 - DEBUG - Signal generated: id=i9j0k1l2m3n4o5p6, timestamp=2020-01-22 14:15:00, entry=1.1089
...
```

---

### WARNING Level (BOTH Mode Conflicts)

```text
2025-10-29 14:30:55 - INFO - Generating BOTH direction signals...
2025-10-29 14:30:56 - WARNING - Conflict detected: timestamp=2020-03-15 12:00:00, pair=EURUSD - Rejecting both signals
2025-10-29 14:30:56 - WARNING - Conflict detected: timestamp=2020-06-20 09:30:00, pair=EURUSD - Rejecting both signals
2025-10-29 14:30:57 - INFO - Signal merge complete: 38 valid signals, 4 conflicts rejected
```

---

## Compatibility

**Python Version**: 3.11+
**Operating Systems**: Windows, Linux, macOS
**Terminal**: PowerShell, Bash, Zsh
**Dependencies**: See pyproject.toml (no new dependencies)

---

## Security Considerations

- No network access required (offline tool)
- Reads local CSV files only (validate paths to prevent directory traversal)
- Writes output files with user permissions
- No credential handling or sensitive data exposure
