# Quickstart: Portfolio Mode Visualization

How to run and verify the fixed portfolio visualization.

## Running a Portfolio Backtest

Command line usage remains similar, but internal execution and output are fixed.

```bash
# Run portfolio mode on two pairs with visualization
poetry run python -m src.cli.run_backtest \
    --pair EURUSD USDJPY \
    --portfolio-mode \
    --visualize \
    --viz-start 2023-01-01
```

### Expected Behavior

1. **Console Output**:

   - You should see "Starting portfolio simulation..." **once**.
   - You should **NOT** see "Starting directional backtest..." for individual symbols afterwards.
   - Execution should exit cleanly after "Results written to..."

2. **Visualization**:
   - A browser window (or HTML file) will open.
   - **Check**: Vertical layout with:
     - **Panel 1**: EURUSD Price Chart (with EURUSD trades only)
     - **Panel 2**: USDJPY Price Chart (with USDJPY trades only)
     - **Panel 3**: Portfolio Value Curve (Shared Equity)
   - **Check**: Crosshair should synchronize time across all panels.
