# Release History

This document tracks all official releases of the trading-strategies project.

## Release Guidelines

- Follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH
- Create GitHub releases from this branch after merging to main
- Tag format: `v{version}` (e.g., `v0.0.1`, `v1.0.0`)
- Include changelog excerpt in release notes
- Attach any relevant artifacts (test results, benchmarks)

## Version Status

### Current Version: 0.5.0

- **Status**: Released
- **Date**: 2026-01-31
- **Branch**: main
- **PR**: #69

---

## Released Versions

### [v0.5.0] - 2026-01-31

**Theme**: CLI Expansion: Scaffold & Ingest

**Highlights**:

- **Strategy Scaffolding**: New `quantpipe scaffold` command to instantly generate boilerplate for new trading strategies.
- **Unified Data Ingestion**: Migrated data processing tools to `quantpipe ingest`, archiving legacy scripts.
- **Integration Test Reliability**: Fixed critical parameter naming and signal generation bugs in the integration test suite.
- **Documentation Update**: Comprehensive updates to docs reflecting the new CLI structure.

**Key Features**:

Strategy Scaffolding:

- `quantpipe scaffold <name>`: Generates directory structure, strategy class, and config.
- Auto-registration of new strategies (optional with `--no-register`).
- Support for descriptions and tags.

Unified Ingestion:

- `quantpipe ingest`: Replaces legacy `build_dataset.py` script.
- Supports bulk processing (`--all`) or single symbol (`--symbol`).
- Standardized logging and path management.

Quality & Infrastructure:

- **Fix**: Resolved `AttributeError` for `StrategyParameters` in integration tests (PR #66).
- **Fix**: Corrected signal generation logic in integration tests (PR #67).
- **Cleanup**: Removed obsolete `run_long_backtest.py` and `build_dataset.py`.

**Usage**:

```bash
# Create a new strategy
poetry run quantpipe scaffold my_new_strategy --tags "trend,breakout" --description "A simple breakout strategy"

# Process new data
poetry run quantpipe ingest --symbol EURUSD --force
```

**Related**:

- Pull Requests: #65, #66, #67, #68, #69
- Closes Issue: #63

### [v0.4.0] - 2026-01-23

**Theme**: Unified CLI & Packaging

**Highlights**:

- **Unified Entry Point**: Replaced manual module execution with a standardized `quantpipe` console command.
- **Subcommand Architecture**: Introduced `backtest` subcommand to house primary simulation logic, paving the way for `ingest` and `optimize` commands.
- **Improved Performance Metrics**: Refactored `run_backtest.py` to better handle `PortfolioResult` objects and standardized JSON/Text output formatting.
- **Visual Stability**: Enhanced `datashader_viz.py` stability for portfolio results via robust duck-typing for symbol detection.

**Key Features**:

QuantPipe CLI:

- `quantpipe backtest` subcommand supporting all legacy flags.
- `--output-format json` support for portfolio-mode results.
- Automatic installation via `pip install .` or `poetry install`.

Refactoring & Quality:

- Extraction of core CLI logic into reusable parser and commander functions.
- Fixed `AttributeError` in results formatting for multi-symbol simulations.
- Resolved integration test regressions across the suite.

**Usage**:

```bash
# Standard Backtest
quantpipe backtest --direction BOTH --pair EURUSD --dataset test

# Multi-Symbol Portfolio
quantpipe backtest --pair EURUSD USDJPY GBPUSD --visualize
```

**Related**:

- Spec: 028-package-quantpipe-cli
- Pull Request: #64
- Closes Issue: #57

### [v0.3.0] - 2026-01-22

**Theme**: CTI Prop Firm Integration & Advanced Metrics

**Highlights**:

- Full simulation of City Traders Imperium (CTI) programs: 1-Step, 2-Step, and Instant Funding.
- Account scaling logic with 4-month periodic reviews and "Independent Lives" tracking (reset on failure).
- Institutional-grade metrics: Sortino Ratio, Sharpe Ratio, Risk-to-Reward, Profit Factor, Win/Loss Streaks.
- Advanced visualization of scaling attempts and tier progression.

**Key Features**:

CTI Integration:

- `--cti-mode` (1STEP, 2STEP, INSTANT) argument.
- `--cti-scaling` flag for multi-year career simulation.
- Automatic enforcement of Daily Loss and Max Drawdown rules.
- "Instant Funding" support with specific parameter schema.

Advanced Metrics:

- Sortino Ratio (downside deviation focus).
- Average Trade Duration.
- Max Consecutive Wins/Losses.
- Metrics calculated per "Life" in scaling mode.

Refactoring:

- Decoupled configuration loading (`src/risk/prop_firm/loader.py`).
- Pydantic V2 migration for core models.
- Extensive linting and cleanup of risk modules.

**Usage**:

```bash
# Run CTI 1-Step Challenge
poetry run python -m src.cli.run_backtest --pair EURUSD --cti-mode 1STEP --starting-balance 10000

# Run CTI Scaling Simulation with Instant Funding
poetry run python -m src.cli.run_backtest --pair EURUSD --cti-mode INSTANT --cti-scaling --starting-balance 2500
```

**Related**:

- Spec: 027-cti-metrics-progression
- Pull Request: #61
- Closes Issues: #24, #60

---

### [v0.2.3] - 2026-01-14

**Theme**: Decoupled Indicators & Parallel Parameter Sweeps

**Highlights**:

- **Parallel Parameter Sweeps**: Interactive CLI for defining and running strategy parameter sweeps across thousands of combinations in parallel.
- **Decoupled Indicators**: Strategies now define their own custom indicators, removing the need for global registry modification.
- **Risk Management Fixes**: CLI risk arguments (R:R, ATR mult, Risk %) now correctly override configuration defaults.

**Key Features**:

Parallel Parameter Sweep:

- Interactive prompts: `--test-range` triggers wizard for strategy params
- Parallel execution: Vectorized backtests run on multiple cores
- Semantic constraints: Filters invalid combinations (e.g., fast > slow)
- Export: Results saved to CSV for analysis

Decoupled Indicators:

- `Strategy.get_custom_indicators()` protocol method
- Custom precedence: Strategy indicators override global built-ins
- No more core code modification needed for custom logic

Risk Argument Fixes:

- `--rr-ratio`, `--atr-mult`, `--risk-pct` correctly wired
- `--max-position-size` enforcement
- Configuration precedence: CLI > Config File > Defaults

**Usage**:

```bash
# Interactive Parameter Sweep
poetry run python -m src.cli.run_backtest --strategy trend-pullback --test-range

# Custom Strategy with standard indicators
poetry run python -m src.cli.run_backtest --strategy my-custom-strat
```

**Related**:

- Feature Specs: 024-parallel-param-sweep, 025-fix-risk-args, 026-decouple-indicators
- Pull Requests: #58, #59
- Issues Closed: #54, #57 (related)

---

### [v0.2.2] - 2025-12-30

**Theme**: Session Blackouts + High-Impact News Avoidance

**Highlights**:

- Block new trade entries during high-impact news events (NFP, IJC)
- Block entries during low-liquidity session gaps (NY close → Asian open)
- Session-only trading mode to whitelist specific sessions (NY, London, Asia, Sydney)
- Rule-based calendar generation without external API dependencies

**Key Features**:

News Blackouts:

- NFP (first Friday) and IJC (every Thursday) at 08:30 ET
- U.S. market holiday detection (NYSE calendar)
- Configurable pre/post event timing offsets
- DST-aware timezone conversion

Session Blackouts:

- NY close (17:00 ET) → Asian open (09:00 Tokyo) gap filtering
- Configurable session anchors and timing

Session-Only Trading (NEW):

- Whitelist approach: `--trade-sessions NY LONDON`
- 4 sessions: NY, London, Asia, Sydney
- Overlapping sessions automatically merge

Technical:

- Vectorized `filter_blackout_signals()` using NumPy boolean masks
- New `src/risk/blackout/` module (config, calendar, holidays, windows, sessions)
- 93 new tests (77 unit + 16 session-only)

**Usage**:

```python
from src.risk.blackout import BlackoutConfig, NewsBlackoutConfig, SessionOnlyConfig

# News blackouts
config = BlackoutConfig(news=NewsBlackoutConfig(enabled=True))

# Session-only trading
config = BlackoutConfig(
    session_only=SessionOnlyConfig(
        enabled=True,
        allowed_sessions=["NY", "LONDON"]
    )
)
```

**Related**:

- Pull Request: #52
- Closes Issue: #19
- Spec: 023-session-blackouts
- Tests: 93 passing (5 test files)

---

### [v0.2.1] - 2025-12-25

**Theme**: Decoupled Risk Management

**Highlights**:

- Runtime risk policy switching via CLI/config without code changes
- Pluggable stop, take-profit, and position sizing policies
- Trailing stop support with ratchet behavior
- 50 new risk-specific tests

**Key Features**:

Risk Policy Architecture:

- `RiskConfig` pydantic model for validation and defaults
- `RiskManager` with `build_orders()` and `update_trailing()` methods
- Protocol-based policies: `StopPolicy`, `TakeProfitPolicy`, `PositionSizer`
- String-based policy registry for runtime selection

CLI Arguments:

- `--risk-pct` (0.25 default)
- `--stop-policy ATR|ATR_Trailing|FixedPips`
- `--atr-mult`, `--atr-period`, `--fixed-pips`
- `--tp-policy RiskMultiple|None`
- `--rr-ratio`
- `--risk-config config.json`

Data Models:

- `Signal` - lightweight strategy output (symbol, direction, timestamp)
- `OrderPlan` - complete order specification with stop, target, size
- `BacktestResult.risk_label` for backtest metadata

**Usage**:

```bash
# ATR trailing stop with 3:1 RR
poetry run python -m src.cli.run_backtest --pair EURUSD --direction LONG \
  --stop-policy ATR_Trailing --atr-mult 2.0 --tp-policy RiskMultiple --rr-ratio 3.0

# Load from JSON config file
poetry run python -m src.cli.run_backtest --pair EURUSD --risk-config risk_config.json
```

**Related**:

- Pull Request: #50
- Closes Issue: #12
- Spec: 021-decouple-risk-management
- Tests: 50 passing (6 test files)

---

### [v0.2.0] - 2025-12-24

**Theme**: Unified Backtest Architecture & Enhanced Visualization

**Highlights**:

- Unified backtest code path for single and multi-symbol runs
- Dynamic position sizing with compounding based on current equity
- Enhanced visualization tooltips with portfolio tracking info
- Portfolio curve shows actual balance (not cumulative P&L)

**Key Features**:

Unified Architecture:

- Removed `--portfolio-mode` CLI flag
- All backtests (1 or N symbols) use `run_portfolio_backtest()`
- Single shared account with unified capital pool
- Consistent position filtering across all modes

Dynamic Position Sizing:

- Risk per trade calculated as % of current equity
- Compounding effect: position sizes adjust as portfolio grows/shrinks
- `portfolio_balance_at_exit`, `risk_percent`, `risk_amount` tracked per trade

Enhanced Visualization Tooltips:

- Entry markers: position_size, tp_value, sl_value (from strategy levels)
- Exit markers: portfolio_balance, risk_percent, risk_value, pnl_dollars
- TP/SL values calculated dynamically from strategy price levels

Portfolio Curve Improvements:

- Shows actual portfolio balance instead of cumulative P&L with fixed risk
- Crosshair with hover tooltip showing balance at cursor position
- Correctly reflects compounding effect

**Usage**:

```bash
poetry run python -m src.cli.run_backtest --pair EURUSD --direction BOTH --visualize --starting-balance 2500
```

**Related**:

- Pull Request: #49
- Branch: 020-fix-backtest-returns

---

### [v0.1.2] - 2025-12-21

**Theme**: Multi-Symbol Backtest Visualization

**Highlights**:

- Enable visualization of multi-symbol backtest results
- Synchronized x-axis navigation with independent y-axis per symbol
- Oscillator panels (RSI/StochRSI) per symbol
- Crosshair tools on all panels
- Portfolio equity curve at bottom

**Key Features**:

Multi-Symbol Visualization:

- Stacked price charts per symbol (vertically arranged)
- Independent y-axis scales (EURUSD ~1.0 vs USDJPY ~145)
- Synchronized x-axis pan/zoom across all panels
- Trade markers per symbol (no cross-contamination)
- TP/SL lines rendered correctly per symbol

Enhanced Data Flow:

- Enriched data with indicators passed to visualization
- Proper tuple unpacking and argument passing fixed
- 5+ symbol warning for layout readability

**Usage**:

```bash
poetry run python -m src.cli.run_backtest --pair EURUSD USDJPY --direction BOTH --visualize
```

**Related**:

- Feature Spec: 016-multi-symbol-viz
- Pull Request: #44
- Closes Issue: #42

---

### [v0.1.1] - 2025-12-21

**Theme**: Multi-Timeframe Backtesting

**Highlights**:

- Run backtests on any timeframe (5m, 15m, 1h, 4h, etc.)
- OHLCV resampling with caching for fast repeated runs
- Timeframe in output filenames and visualization titles
- Config file support with `--config` flag

**Key Features**:

- `--timeframe` CLI argument (default: 1m, supports Xm/Xh/Xd formats)
- Polars-based resampling with `bar_complete` data quality flag
- Disk caching in `.time_cache/` directory
- YAML config file defaults with CLI precedence
- Visualization zoom shows last 60 candles (works for any timeframe)

**Documentation**:

- `docs/timeframes.md` usage guide
- `backtest_config.yaml.example`
- GitHub issue/PR templates
- Constitution v1.10.0 (Principle XIII: GitHub Workflow Templates)

**Related**:

- Feature Spec: 015-multi-timeframe-backtest
- Pull Request: #43
- Closes Issue: #18

---

### [v0.1.0] - 2025-12-20

**Theme**: Interactive Visualization & Multi-Symbol Portfolio Support

**Highlights**:

- **Interactive Visualization**: Full backtest charting with HoloViews/Bokeh
- **Multi-Symbol Backtesting**: Run portfolios across multiple currency pairs
- **500,000+ Candle Support**: High-performance rendering with Datashader
- **Comprehensive Metrics Panel**: Win rate, expectancy, profit factor, drawdown

**Key Features**:

Visualization (`--visualize`):

- OHLC candlestick chart with custom hover tooltips
- EMA overlays (20/50/200) on price chart
- StochRSI oscillator panel (0-1 scale with center line)
- Trade markers: entry triangles, exit diamonds
- TP/SL level lines (last 100 trades)
- Portfolio value curve
- Linked x-axis panning across all charts

Multi-Symbol Portfolio:

- Independent and portfolio execution modes
- Correlation tracking with configurable thresholds
- Dynamic position allocation
- Symbol filtering at runtime

Performance:

- Vectorized scanning (6.9M candles in ~0.02s)
- Direct Parquet loading (10-15x speedup)
- Trade lines limited to 100 for rendering performance

**Documentation**:

- New: `docs/visualization.md` - Complete visualization guide
- Updated: README.md with Interactive Visualization section

**Related**:

- Feature Specs: 011-optimize-batch-simulation, 014-interactive-viz
- Issues Closed: #32
- Pull Request: #36

---

### [v0.0.1] - 2025-11-12

**Theme**: Scan & Simulation Performance Optimization

**Highlights**:

- High-performance vectorized scanning (6.9M candles in ~0.02s)
- Complete trade execution pipeline with metrics
- Rich progress bars with clean terminal output
- Auto-constructed data paths from CLI flags
- Direct Parquet loading (10-15x speedup over CSV)

**Key Features**:

- BatchScan with strategy.scan_vectorized() protocol
- SimulationResult with 10 trade detail arrays
- TradeExecution conversion and metrics calculation
- CLI auto-path: `--pair EURUSD --dataset test`
- Smart file format detection (.parquet/.csv fallback)

**Code Quality**:

- All modules ≥9.78/10 Pylint scores
- 16 files changed, 680 insertions, 88 deletions
- New test script: `scripts/test_vectorized_scan.py`

**Related**:

- Feature Spec: 010-scan-sim-perf
- Pull Request: #27
- Commit: a723ed0

---

## Roadmap

### Next Up (Scheduled)

| Priority | Issue | Feature                                            |
| -------- | ----- | -------------------------------------------------- |
| 1        | #8    | User portfolio prompt with default risk parameters |
| 2        | #24   | City Traders Imperium funded account progression   |
| 3        | #26   | Interactive prompts for missing backtest flags     |
| 4        | #13   | Runtime prompts for strategy & risk params         |
| 5        | #39   | Forward testing module (multi-platform)            |
| 6        | #40   | Market regime discovery (HDBSCAN clustering)       |
| 7        | #23   | Optional GPU acceleration (CUDA)                   |
| 8        | #16   | Z-Score mean reversion strategy                    |

### Backlog

| Issue | Feature                                                           |
| ----- | ----------------------------------------------------------------- |
| #41   | Next.js-based GUI (long-term)                                     |
| #2    | Multi-Strategy, Multi-Currency, Platform Integration (meta-issue) |

### v1.0.0 (Future Major Release)

- Stable public API
- Production-ready backtesting engine
- Comprehensive strategy library
- Full documentation and examples
