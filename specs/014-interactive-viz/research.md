# Research: Interactive Backtest Visualization

## Decision: Visualization Library

**Decision**: Use `lightweight-charts-python`.

**Rationale**:

- **Performance**: Optimized for financial data and capable of handling large datasets (millions of points) with smooth panning/zooming, unlike Plotly which degrades significantly with >100k points in interactive mode.
- **Suitability**: Specifically designed for candlestick/OHLCV data with built-in features for overlays and indicators.
- **Interactivity**: Provides native zoom, pan, and hover tooltips out-of-the-box.
- **Architecture**: Separates data processing (Python) from rendering (JS/Webview), tapping into TradingView's lightweight-charts engine.

**Alternatives Considered**:

- **Plotly**: Good for general purpose, but performance is a known bottleneck for 1-minute data over long periods (10 years = ~3.7M rows).
- **Bokeh**: High performance, but requires more boilerplate to achieve the specific look-and-feel of financial trading charts compared to a dedicated library.
- **mplfinance**: Static images primarily; interactive mode is limited compared to web-based solutions.

## Decision: Data Integration

**Decision**: Pass data directly from CLI/Orchestrator context to Visualization module.

**Rationale**:

- `BacktestResult` objects do not (and should not) store the heavy OHLCV dataframe to keep serialization lightweight.
- `src/cli/run_backtest.py` already computes `enriched_df` (indicators + candles) before running the backtest.
- The visualization function can accept `enriched_df` (for price/indicators) and `BacktestResult` (for trade markers) as independent arguments.

## Decision: Multi-Symbol Handling

**Decision**: Sequential blocking visualization.

**Rationale**:

- Spawning multiple windows simultaneously for 10+ symbols would overwhelm system resources and the user.
- If `--visualize` is enabled for a multi-symbol run, the system will display charts one by one (waiting for user to close window) or only display the specific symbol requested via an additional filter. For MVP, sequential display or "single symbol only" restriction is prudent.
