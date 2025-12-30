# Implementation Plan: Session Blackouts + High-Impact News Avoidance

**Branch**: `023-session-blackouts` | **Date**: 2025-12-28 | **Spec**: [spec.md](file:///e:/GitHub/trading-strategies/specs/023-session-blackouts/spec.md)  
**Input**: Feature specification from `/specs/023-session-blackouts/spec.md`

## Summary

Add optional backtesting flags to block new trade entries during:

1. **News blackout windows** (NFP, IJC events) - configurable time windows around scheduled economic releases
2. **Session blackout windows** (NY close → Asian open) - low-liquidity periods

The implementation integrates into `src.risk` as optional configuration policies, using rule-based calendar generation without external API dependencies.

## Technical Context

**Language/Version**: Python 3.11+ (per pyproject.toml)  
**Primary Dependencies**: pydantic (validation), pandas/polars (timestamps), pytz (timezone handling)  
**Storage**: N/A (in-memory calendar generation, optional CSV/Parquet export)  
**Testing**: pytest with existing unit/integration test patterns  
**Target Platform**: Windows/Linux CLI backtester  
**Project Type**: Single project (existing `src/` structure)  
**Performance Goals**: Calendar generation < 100ms for 20-year date range  
**Constraints**: Fully offline, no external API calls, deterministic output, **vectorized filtering (no per-candle loops)**  
**Scale/Scope**: NFP + IJC event types initially; session windows for NY/Asian

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Gate                            | Requirement                                             | Status     |
| ------------------------------- | ------------------------------------------------------- | ---------- |
| II. Risk Management Integration | Feature integrates into `src.risk` module               | ✅ Pass    |
| III. Backtesting & Validation   | Blackouts enhance backtest realism                      | ✅ Pass    |
| VIII. Code Quality              | Pydantic models with validation, docstrings, type hints | ✅ Planned |
| IX. Dependency Management       | Use `poetry add` for any new deps                       | ✅ Planned |
| X. Code Quality Automation      | pytest, ruff, black compliance                          | ✅ Planned |

**No constitution violations detected.**

## Project Structure

### Documentation (this feature)

```text
specs/023-session-blackouts/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── risk/
│   ├── blackout/                  # [NEW] Blackout module
│   │   ├── __init__.py
│   │   ├── config.py              # [NEW] BlackoutConfig pydantic model
│   │   ├── calendar.py            # [NEW] Rule-based event generation
│   │   ├── windows.py             # [NEW] Blackout window logic
│   │   └── holidays.py            # [NEW] U.S. market holiday detection
│   ├── __init__.py                # [MODIFY] Export blackout components
│   └── config.py                  # [MODIFY] Add optional BlackoutConfig
└── backtest/
    ├── signal_filter.py           # [MODIFY] Add blackout filtering
    └── orchestrator.py            # [MODIFY] Wire blackout checks

tests/
├── unit/
│   ├── blackout/                  # [NEW] Unit test directory
│   │   ├── test_calendar.py       # [NEW] Calendar generation tests
│   │   ├── test_windows.py        # [NEW] Window merge/overlap tests
│   │   ├── test_holidays.py       # [NEW] Holiday detection tests
│   │   └── test_config.py         # [NEW] Config validation tests
└── integration/
    └── test_blackout_backtest.py  # [NEW] End-to-end blackout test
```

**Structure Decision**: Blackout logic is grouped in a new `src/risk/blackout/` subpackage to maintain clean separation while integrating into the existing risk module.

---

## Proposed Changes

### Component 1: Blackout Configuration

#### [NEW] [config.py](file:///e:/GitHub/trading-strategies/src/risk/blackout/config.py)

Pydantic models for blackout configuration:

- `NewsBlackoutConfig`: `enabled`, `pre_close_minutes`, `post_pause_minutes`, `force_close`
- `SessionBlackoutConfig`: `enabled`, `pre_close_minutes`, `post_pause_minutes`, `ny_close_time`, `asian_open_time`
- `BlackoutConfig`: Composite config holding news + session settings with defaults

---

### Component 2: Calendar Generation

#### [NEW] [calendar.py](file:///e:/GitHub/trading-strategies/src/risk/blackout/calendar.py)

Rule-based economic event calendar:

- `generate_nfp_events(start_date, end_date)`: First Friday of each month at 08:30 ET
- `generate_ijc_events(start_date, end_date)`: Every Thursday at 08:30 ET
- `generate_news_calendar(start_date, end_date, event_types)`: Aggregate generator
- Returns `NewsEvent` dataclass with `event_time_utc`, `blackout_start_utc`, `blackout_end_utc`

#### [NEW] [holidays.py](file:///e:/GitHub/trading-strategies/src/risk/blackout/holidays.py)

U.S. market holiday detection:

- `is_us_market_holiday(date)`: Check if date is a major U.S. market holiday
- Covers: New Year's, MLK Day, Presidents Day, Good Friday, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas

---

### Component 3: Window Logic

#### [NEW] [windows.py](file:///e:/GitHub/trading-strategies/src/risk/blackout/windows.py)

Blackout window management:

- `BlackoutWindow` dataclass: `start_utc`, `end_utc`, `source`
- `expand_news_windows(events, config)`: Generate windows from news events
- `expand_session_windows(date_range, config)`: Generate daily session windows
- `merge_overlapping_windows(windows)`: Combine overlapping/adjacent windows
- `is_in_blackout(timestamp, windows)`: Binary check for entry blocking

---

### Component 4: Integration

#### [MODIFY] [signal_filter.py](file:///e:/GitHub/trading-strategies/src/backtest/signal_filter.py)

Add blackout-aware filtering:

- `filter_blackout_signals(signal_indices, timestamps, blackout_windows)`: **Vectorized** removal of signals within blackout periods using NumPy boolean masks (no per-candle loops)

#### [MODIFY] [config.py](file:///e:/GitHub/trading-strategies/src/risk/config.py)

Add optional blackout configuration to `RiskConfig`:

- Add `blackout: BlackoutConfig | None = None` field
- Maintain backward compatibility (None = disabled)

---

## Verification Plan

### Automated Tests

**Unit Tests** (run with `poetry run pytest tests/unit/blackout/ -v`):

1. **test_calendar.py**

   - `test_nfp_first_friday_of_month`: Verify NFP lands on correct dates
   - `test_ijc_every_thursday`: Verify IJC every Thursday
   - `test_calendar_deterministic`: Same inputs → same outputs
   - `test_calendar_handles_dst`: Correct UTC around DST transitions
   - `test_calendar_skips_holidays`: No events on U.S. holidays

2. **test_holidays.py**

   - `test_known_holidays_detected`: Fixed holidays (July 4, Christmas)
   - `test_floating_holidays_detected`: Thanksgiving, MLK Day
   - `test_non_holiday_returns_false`: Regular trading days not flagged

3. **test_windows.py**

   - `test_window_merge_overlapping`: Overlapping windows combine
   - `test_window_merge_adjacent`: Adjacent windows combine
   - `test_window_merge_disjoint`: Non-overlapping windows stay separate
   - `test_is_in_blackout_true`: Timestamp inside window
   - `test_is_in_blackout_false`: Timestamp outside window

4. **test_config.py**
   - `test_default_config_disabled`: Both flags default False
   - `test_config_validation`: Pydantic constraints enforced

**Integration Tests** (run with `poetry run pytest tests/integration/test_blackout_backtest.py -v`):

1. `test_backtest_blocks_entries_during_news`: Run backtest with `news.enabled=True`, verify no entries in NFP window
2. `test_backtest_blocks_entries_during_session`: Run backtest with `sessions.enabled=True`, verify no entries in session gap
3. `test_backtest_allows_entries_when_disabled`: Verify normal behavior with both flags False

### Manual Verification

1. Generate a calendar for 2023 and spot-check NFP dates against historical records
2. Run existing backtest with blackouts enabled and compare trade count reduction
