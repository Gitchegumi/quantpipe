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

# Run tests with coverage
poetry run pytest --cov=src
```

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
