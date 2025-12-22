# Release History

This document tracks all official releases of the trading-strategies project.

## Release Guidelines

- Follow [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH
- Create GitHub releases from this branch after merging to main
- Tag format: `v{version}` (e.g., `v0.0.1`, `v1.0.0`)
- Include changelog excerpt in release notes
- Attach any relevant artifacts (test results, benchmarks)

## Version Status

### Current Version: 0.1.1

- **Status**: Released
- **Date**: 2025-12-21
- **Branch**: 015-multi-timeframe-backtest
- **PR**: #43

---

## Released Versions

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

## Version Planning

### v0.2.0 (Next Minor Release)

- Multi-symbol visualization support (#42)
- Enhanced reporting and export formats
- Additional strategy implementations

### v1.0.0 (Future Major Release)

- Stable public API
- Production-ready backtesting engine
- Comprehensive strategy library
- Full documentation and examples
