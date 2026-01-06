# Implementation Plan: Parallel Indicator Parameter Sweep

**Branch**: `024-parallel-param-sweep` | **Date**: 2025-12-30 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/024-parallel-param-sweep/spec.md)
**Input**: Feature specification combining GitHub issues #9 and #10

## Summary

Implement an interactive CLI mode (`--test_range`) that discovers indicator parameters from strategy metadata, prompts users for value ranges, generates cartesian product combinations, and executes backtests in parallel using the existing vectorized infrastructure.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Rich (existing), itertools (stdlib), concurrent.futures (via existing parallel.py)
**Storage**: N/A (results in memory, optional CSV export)
**Testing**: pytest (existing)
**Target Platform**: Windows/Linux CLI
**Project Type**: Single Python project
**Performance Goals**: ≥70% parallel efficiency (SC-003), 100 combinations in <15 min (SC-004)
**Constraints**: Must use vectorized scanning, no per-candle loops
**Scale/Scope**: Up to 1000+ parameter combinations

## Constitution Check

_GATE: Must pass before implementation._

| Principle                            | Status          | Notes                                           |
| ------------------------------------ | --------------- | ----------------------------------------------- |
| I. Strategy-First Architecture       | ✅ Pass         | Extends strategy interface, doesn't change core |
| II. Risk Management (NON-NEGOTIABLE) | ✅ Pass         | Each backtest uses existing risk controls       |
| VIII. Code Quality                   | ✅ Will enforce | Black, Ruff, Pylint required                    |
| IX. Dependency Management            | ✅ Pass         | No new dependencies (Rich already installed)    |
| X. Code Quality Automation           | ✅ Will enforce | pytest for all tests                            |
| XI. Commit Message Standards         | ✅ Will follow  | feat(024): format                               |
| XII. Task Tracking                   | ✅ Will follow  | tasks.md updates with commits                   |

## Project Structure

### Documentation (this feature)

```text
specs/024-parallel-param-sweep/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output (complete)
├── quickstart.md        # Phase 1 output (complete)
├── checklists/          # Quality checklists
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code Changes

```text
src/
├── backtest/
│   └── sweep.py                    # [NEW] Parameter sweep orchestration
├── cli/
│   ├── run_backtest.py             # [MODIFY] Add --test_range flag
│   └── prompts/
│       └── range_input.py          # [NEW] Interactive range prompting
├── indicators/
│   └── registry/
│       └── builtins.py             # [MODIFY] Add semantic indicator aliases
└── strategy/
    └── trend_pullback/
        └── strategy.py             # [MODIFY] Update required_indicators to semantic names

tests/
├── unit/
│   ├── test_range_parser.py        # [NEW] Range syntax parsing tests
│   └── test_sweep_generation.py    # [NEW] Cartesian product + filtering tests
└── integration/
    └── test_parameter_sweep.py     # [NEW] End-to-end sweep tests
```

---

## Proposed Changes

### Component 1: Sweep Core Module

#### [NEW] [sweep.py](file:///e:/GitHub/trading-strategies/src/backtest/sweep.py)

New module containing parameter sweep orchestration:

- `ParameterRange` dataclass for single parameter input
- `ParameterSet` dataclass for one combination
- `SweepConfig` dataclass for full sweep configuration
- `SweepResult` dataclass for aggregated results
- `parse_range_input(input_str, default)` → Parse user input to values list
- `generate_combinations(ranges)` → Cartesian product generation
- `filter_invalid_combinations(combinations, constraints)` → Skip invalid, count skipped
- `run_sweep(config, backtest_fn, max_workers)` → Parallel execution wrapper

---

### Component 2: CLI Integration

#### [MODIFY] [run_backtest.py](file:///e:/GitHub/trading-strategies/src/cli/run_backtest.py)

Add arguments and sweep mode entry:

```diff
+ parser.add_argument("--test_range", action="store_true",
+                     help="Enable interactive parameter sweep mode")
+ parser.add_argument("--export", type=str, default=None,
+                     help="Export sweep results to CSV file")
```

Add sweep mode handler in `main()`:

```python
if args.test_range:
    from ..backtest.sweep import run_interactive_sweep
    return run_interactive_sweep(strategy, args)
```

---

#### [NEW] [range_input.py](file:///e:/GitHub/trading-strategies/src/cli/prompts/range_input.py)

Interactive prompting module using Rich:

- `prompt_for_indicator_params(indicator_spec)` → Prompt for each param in spec.params
- `collect_all_ranges(strategy)` → Iterate strategy.metadata.required_indicators
- Display defaults in parentheses, parse range syntax

---

### Component 3: Semantic Indicator Registry

#### [MODIFY] [builtins.py](file:///e:/GitHub/trading-strategies/src/indicators/registry/builtins.py)

Register semantic aliases:

```python
# Add after existing ema20/ema50 registrations
fast_ema_spec = IndicatorSpec(
    name="fast_ema",
    requires=["close"],
    provides=["fast_ema"],
    compute=_ema_wrapper,
    params={"period": 20, "column": "close"},
)

slow_ema_spec = IndicatorSpec(
    name="slow_ema",
    requires=["close"],
    provides=["slow_ema"],
    compute=_ema_wrapper,
    params={"period": 50, "column": "close"},
)
```

---

### Component 4: Strategy Metadata Update

#### [MODIFY] [strategy.py](file:///e:/GitHub/trading-strategies/src/strategy/trend_pullback/strategy.py)

Update to use semantic indicator names:

```diff
  @property
  def metadata(self) -> StrategyMetadata:
      return StrategyMetadata(
          name="trend-pullback",
          version="1.0.0",
-         required_indicators=["ema20", "ema50", "atr14", "stoch_rsi"],
+         required_indicators=["fast_ema", "slow_ema", "atr", "stoch_rsi"],
          tags=["trend-following", "pullback", "momentum"],
      )
```

Also update `scan_vectorized()` to use semantic indicator names in array lookups.

---

## Verification Plan

### Automated Tests

All tests run via: `poetry run pytest <path> -v`

#### Unit Tests

| Test File                             | Command                                                    | What It Verifies                                         |
| ------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------- |
| `tests/unit/test_range_parser.py`     | `poetry run pytest tests/unit/test_range_parser.py -v`     | Range syntax parsing (FR-005, FR-006, FR-007)            |
| `tests/unit/test_sweep_generation.py` | `poetry run pytest tests/unit/test_sweep_generation.py -v` | Cartesian product, constraint filtering (FR-016, FR-019) |

**New test cases to implement**:

1. **test_range_parser.py**:

   - `test_parse_single_value` → `"15"` → `[15]`
   - `test_parse_range_step` → `"10-30 step 5"` → `[10, 15, 20, 25, 30]`
   - `test_parse_empty_uses_default` → `""` with default 20 → `[20]`
   - `test_parse_invalid_raises` → `"abc"` → `ValueError`
   - `test_parse_float_range` → `"0.2-0.4 step 0.1"` → `[0.2, 0.3, 0.4]`

2. **test_sweep_generation.py**:
   - `test_cartesian_product_simple` → 2×2 = 4 combinations
   - `test_filter_fast_gte_slow` → Skip when fast_ema >= slow_ema
   - `test_skipped_count_tracking` → Verify skipped count matches

#### Integration Tests

| Test File                                       | Command                                                              | What It Verifies                            |
| ----------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------- |
| `tests/integration/test_parameter_sweep.py`     | `poetry run pytest tests/integration/test_parameter_sweep.py -v`     | End-to-end sweep execution (FR-020, FR-023) |
| `tests/integration/test_parallel_efficiency.py` | `poetry run pytest tests/integration/test_parallel_efficiency.py -v` | Existing parallel efficiency (SC-003)       |

**New test cases to implement**:

1. **test_parameter_sweep.py**:
   - `test_sweep_with_small_range` → Run 4-combination sweep, verify all complete
   - `test_results_correctly_labeled` → Verify each result has correct param labels (SC-005)
   - `test_sequential_mode` → Verify `--sequential` runs one at a time

### Lint & Format Verification

```bash
# Run before each commit
poetry run black src/backtest/sweep.py src/cli/prompts/range_input.py
poetry run ruff check src/backtest/sweep.py src/cli/prompts/range_input.py
poetry run pylint src/backtest/sweep.py src/cli/prompts/range_input.py --score=yes
```

### Manual Verification

**Interactive CLI Test** (requires user execution):

```bash
# 1. Run with --test_range flag
poetry run python -m src.cli.run_backtest \
    --pair EURUSD \
    --strategy trend_pullback \
    --direction BOTH \
    --test_range

# 2. When prompted:
#    - For fast_ema period: enter "10-20 step 5"
#    - For slow_ema period: enter "50-60 step 10"
#    - Accept defaults for other parameters
#    - Confirm when prompted (should show 6 combinations)

# 3. Verify:
#    - Progress bar updates during execution
#    - Results table shows ranked combinations
#    - Parameter labels are correct
```

---

## Complexity Tracking

No constitution violations requiring justification.

---

## Next Steps

Run `/speckit.tasks` to generate tasks.md with implementation order.
