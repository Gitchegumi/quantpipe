# Feature 027: CTI Progression & Advanced Metrics

## Overview

Implemented CTI Prop Firm logic including Challenge Rules (1-Step, 2-Step) and Account Scaling. Added advanced statistical metrics (Sortino, Avg Duration, Streaks) to standard backtest reports.

## Changes

### 1. Configuration & Models

- **`src.risk.prop_firm.models`**: Added `ChallengeConfig`, `ScalingConfig`, `LifeResult`.
- **`src.risk.prop_firm.loader`**: Implemented JSON config loading for CTI presets.
- **`src.models.core.MetricsSummary`**: Added `sortino_ratio`, `avg_trade_duration`, `max_consecutive_wins/losses`.

### 2. Core Logic

- **`src.risk.prop_firm.evaluator`**:
  - Implemented `evaluate_challenge` to check Daily Loss, Max Drawdown (Static/Trailing), and Profit Targets.
  - Supports "Independent Lives" logic where PnL resets after failure or promotion.
- **`src.risk.prop_firm.scaling`**:
  - Implemented `evaluate_scaling` for multi-stage progression.
  - Handles 4-month review periods and account resets.

### 3. CLI Integration

- Updated `src.cli.run_backtest`:
  - Added `--cti-mode` (1STEP, 2STEP, INSTANT).
  - Added `--cti-scaling` flag.
  - Implemented **Retry Logic** for Challenge Evaluation: If a challenge fails (Drawdown/Daily Loss), the simulation automatically resets balance and starts a "New Life" with remaining data.
  - Generates a summary of Total Passed vs Failed attempts.
  - Validates account size against CTI presets.

## Verification

### Automated Tests

Ran full unit test suite for new components:

```powershell
poetry run pytest tests/unit/prop_firm/
poetry run pytest tests/unit/test_metrics_advanced.py
```

- `test_evaluator.py`: Verified Drawdown and Daily Loss triggers.
- `test_scaling.py`: Verified Promotion, Reset, and Life Aggregation.
- `test_metrics_advanced.py`: Verified Sortino and streak calculations.

### CLI Verification

Verified argument registration:

```powershell
poetry run python -m src.cli.run_backtest --help
```

Arguments `--cti-mode` and `--cti-scaling` are correctly registered.

## Usage Example

```powershell
# Run CTI 1-Step Challenge on EURUSD
poetry run python -m src.cli.run_backtest --direction LONG --cti-mode 1STEP --starting-balance 10000 --pair EURUSD

# Run CTI Scaling Simulation
poetry run python -m src.cli.run_backtest --direction LONG --cti-mode 1STEP --cti-scaling \
--starting-balance 10000 --pair EURUSD
```
