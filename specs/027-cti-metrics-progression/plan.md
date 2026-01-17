# Implementation Plan - Enhancing Result Output

## Goal Description

Enhance the backtest results output (both standard and CTI reports) to include:

1. **Strategy Name** in the Metadata section.
2. **Streak Metrics** (Longest Winning/Losing Streak) in the Performance Metrics section.
3. **Life-Level Stats** (Wins, Losses, Streaks) in the CTI Evaluation output.

## User Review Required

> [!NOTE] > `BacktestResult` model will safely ignore the new `strategy_name` field if not populated, maintaining backward compatibility.

## Proposed Changes

### Formatters

#### [MODIFY] src/data_io/formatters.py

- Update `format_text_output` to accept `strategy_name` argument.
- Update `format_text_output` to print "Strategy: [Name]" in RUN METADATA.
- Update `_format_metrics_summary` to print `Max Consec Wins` and `Max Consec Losses`.

### Evaluator

#### [MODIFY] src/risk/prop_firm/evaluator.py

- Import `calculate_metrics` from `src.backtest.metrics`.
- In `evaluate_challenge`, call `calculate_metrics` on the life's trades and populate `LifeResult.metrics`.

### CLI

#### [MODIFY] src/cli/run_backtest.py

- Pass `strategy_name` (e.g. `strategy.__class__.__name__`) to `format_text_output`.
- Update CTI reporting block to read `win_count`, `loss_count`, `max_consecutive_wins`, `max_consecutive_losses` from `life.metrics` and print them.

## Verification Plan

### Automated Tests

- Run `poetry run python -m src.cli.run_backtest --cti-mode 1STEP --starting-balance 2500 --pair EURUSD --direction BOTH`
- Verify output file contains:
  - `Strategy: [StrategyName]` in metadata.
  - `Max Consec Wins/Losses` in global metrics.
  - `Wins: X, Losses: Y, Max Win Streak: A, Max Loss Streak: B` in CTI Life reports.
