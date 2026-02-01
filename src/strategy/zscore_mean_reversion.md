# Z-Score Mean Reversion Strategy

## Overview
The Z-Score Mean Reversion strategy is a statistically grounded approach to identifying overbought and oversold conditions. Unlike traditional indicators like Bollinger Bands that use absolute price levels, this strategy uses the **Z-Score** to quantify how many standard deviations the current price is away from its rolling mean.

## Philosophy
Markets often exhibit "snap-back" behavior when prices deviate significantly from their average. By framing price movement in statistical terms (standard deviations), we can identify "unusual" price action with mathematical rigor. This strategy provides a clean, deterministic baseline for evaluating mean-reversion behavior.

## How It Works

### 1. Statistical Computation
The strategy calculates the Z-Score using a configurable rolling window (default: 100 bars):
- **Mean ($\mu$):** The average price over the window.
- **Std Dev ($\sigma$):** The standard deviation of price over the window.
- **Z-Score:** $(Price - \mu) / \sigma$

### 2. Entry Triggers
- **Long Entry**: Triggered when the Z-Score falls below the lower threshold (e.g., $-2.0$), indicating the price is significantly "oversold" relative to its recent history.
- **Short Entry**: Triggered when the Z-Score rises above the upper threshold (e.g., $+2.0$), indicating the price is significantly "overbought."

### 3. Exit Triggers
The strategy supports two exit mechanisms:
- **Mean Reversion**: The position is closed when the Z-Score returns to a "neutral" level (default: $0.0$), signaling that the price has reverted to its mean.
- **Time Exit**: A failsafe exit after a fixed number of bars (holding period) to prevent being trapped in a trending market that doesn't mean-revert.

## Parameters
- `rolling_window`: The number of lookback bars for mean and standard deviation (default: 100).
- `threshold`: The standard deviation multiplier for entries (default: 2.0).
- `holding_period`: Maximum number of bars to hold a position (default: 20).
