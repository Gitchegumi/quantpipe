# trading-strategies Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-26

## Active Technologies

- Python 3.11 (chosen for ecosystem breadth, numerical libs, readability) + numpy (vector math), pandas (time series handling), ta-lib or custom EMA/ATR/RSI fallback implementation, pydantic (config validation), rich/logging (structured logs), pytest (tests) (001-trend-pullback)

## Project Structure

```text
src/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11: MUST follow PEP 8 style guidelines. All modules, classes, methods, and functions MUST include complete docstrings (PEP 257). Use type hints for all signatures. Line length ≤88 characters (Black standard). See Constitution Principle VIII for full requirements.

## Recent Changes

- 001-trend-pullback: Added Python 3.11 (chosen for ecosystem breadth, numerical libs, readability) + numpy (vector math), pandas (time series handling), ta-lib or custom EMA/ATR/RSI fallback implementation, pydantic (config validation), rich/logging (structured logs), pytest (tests)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
