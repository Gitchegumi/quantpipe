# Trading Strategies

Algorithmic FX trading strategies with comprehensive backtesting framework.

## Overview

This project implements a parsimonious trend pullback continuation strategy for FX markets. The strategy identifies high-probability entry points by waiting for pullbacks in the prevailing trend, confirmed by reversal patterns and momentum indicators.

## Quick Start

See [specs/001-trend-pullback/quickstart.md](specs/001-trend-pullback/quickstart.md) for detailed setup and usage instructions.

## Installation

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run tests
poetry run pytest
```

## Project Structure

```text
src/
├── indicators/          # Technical indicators (EMA, ATR, RSI)
├── strategy/            # Trading strategy logic
│   └── trend_pullback/  # Trend pullback continuation strategy
├── risk/                # Position sizing and risk management
├── backtest/            # Backtesting engine
├── models/              # Data models and entities
├── io/                  # Data ingestion and manifest handling
├── cli/                 # Command-line interface
└── config/              # Configuration management

tests/
├── unit/                # Unit tests
├── integration/         # Integration tests
├── performance/         # Performance benchmarks
└── fixtures/            # Test data fixtures
```

## Features

- **Trend Detection**: EMA-based trend classification with ranging market filter
- **Pullback Identification**: Price retracement detection with momentum confirmation
- **Reversal Confirmation**: Candle pattern recognition and momentum turn validation
- **Risk Management**: ATR-based stops, position sizing, drawdown protection
- **Backtesting**: Streaming data processing, deterministic results, comprehensive metrics
- **Reproducibility**: Hash-based result verification, data provenance tracking

## Requirements

- Python 3.11+
- Poetry for dependency management

## Development

```bash
# Run linter
poetry run ruff check .

# Format code
poetry run black src/ tests/

# Run pylint
poetry run pylint src/ --score=yes

# Run tests with coverage
poetry run pytest --cov=src
```

## Configuration

The strategy accepts configuration via `src/config/parameters.py` using Pydantic models.

### Core Parameters

**Trend Classification:**

- `ema_fast_period`: Fast EMA period (default: 12)
- `ema_slow_period`: Slow EMA period (default: 50)
- `range_threshold`: Percentage threshold for ranging market detection (default: 0.005 = 0.5%)

**Pullback Detection:**

- `pullback_ema_period`: EMA for pullback reference (default: 12)
- `pullback_threshold`: Minimum retracement percentage (default: 0.003 = 0.3%)
- `pullback_max_age`: Maximum candles since pullback (default: 5)

**Reversal Confirmation:**

- `reversal_candle_types`: Enabled patterns (default: `["hammer", "engulfing"]`)
- `rsi_period`: RSI lookback period (default: 14)
- `rsi_oversold`: Oversold threshold (default: 30)
- `rsi_overbought`: Overbought threshold (default: 70)

**Risk Management:**

- `atr_period`: ATR calculation period (default: 14)
- `atr_stop_multiplier`: ATR multiplier for stop distance (default: 2.0)
- `risk_per_trade`: Risk percentage per trade (default: 0.01 = 1%)
- `max_position_pct`: Maximum position size (default: 0.02 = 2%)

**Exit Logic:**

- `target_r_multiple`: Profit target in R-multiples (default: 3.0)
- `trailing_stop_activation_r`: R-multiple to activate trailing stop (default: 1.5)
- `trailing_stop_distance_r`: Trailing stop distance in R (default: 1.0)

**Optional Filters:**

- `volatility_filter_enabled`: Enable volatility regime filtering (default: False)
- `htf_filter_enabled`: Enable higher timeframe confirmation (default: False)
- `htf_timeframe_multiplier`: HTF multiplier (default: 4)
- `htf_ema_period`: HTF EMA period (default: 50)

### Example Configuration

```python
from src.config.parameters import StrategyParameters

params = StrategyParameters(
    ema_fast_period=12,
    ema_slow_period=50,
    atr_period=14,
    atr_stop_multiplier=2.0,
    risk_per_trade=0.01,
    target_r_multiple=3.0,
)
```

### Environment Variables

Set via `.env` file or environment:

- `LOG_LEVEL`: Logging level (default: `INFO`)
- `DATA_DIR`: Data directory path (default: `./data`)
- `OUTPUT_DIR`: Backtest output directory (default: `./runs`)

## Documentation

- [Feature Specification](specs/001-trend-pullback/spec.md)
- [Implementation Plan](specs/001-trend-pullback/plan.md)
- [Data Model](specs/001-trend-pullback/data-model.md)
- [Quickstart Guide](specs/001-trend-pullback/quickstart.md)

## License

Proprietary - All Rights Reserved

## Constitution Compliance

This project adheres to the [Trading Strategies Constitution](.specify/memory/constitution.md), ensuring:

- Strategy-first architecture
- Integrated risk management
- Comprehensive backtesting and validation
- Real-time performance monitoring
- Data integrity and provenance
- Model parsimony and interpretability
