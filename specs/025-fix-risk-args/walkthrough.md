# Walkthrough - Fix Risk CLI Arguments (Issue #53)

I have implemented the fix for Issue #53, ensuring that risk-related CLI arguments are correctly mapped to strategy parameters and take precedence over configuration file settings.

## Changes

### 1. `src/cli/run_backtest.py`

- Refactored parameter resolution logic to prioritize CLI arguments > Config file > Default values.
- Removed `default` values from `argparse` definitions for risk arguments to allow distinguishing between "user-provided" and "missing" arguments.
- Added logging of active risk parameters at the start of execution.
- Ensured `risk_config` construction uses the resolved parameters.

### 2. `src/config/parameters.py`

- Added `max_position_size` field to `StrategyParameters` data model.

### 3. `tests/integration/test_cli_risk_args.py`

- Created a new integration test suite to verify:
  - CLI arguments override default values.
  - CLI arguments override configuration file values.
  - Defaults are used when no arguments are provided.

## Verification Results

### Automated Tests

The new integration tests passed successfully:

```text
tests/integration/test_cli_risk_args.py ... [100%]
3 passed in 1.35s
```

### Manual Verification Steps

You can verify the fix manually by running the following commands:

1. **Run with defaults:**

   ```bash
   poetry run run_backtest --pair EURUSD --dataset test --direction LONG
   ```

   _Expectation:_ Logs show default risk parameters (Risk: 0.25%, ATR Mult: 2.0).

2. **Run with CLI overrides:**

   ```bash
   poetry run run_backtest --pair EURUSD --dataset test --direction LONG --risk-pct 1.0 --atr-mult 3.0
   ```

   _Expectation:_ Logs show Risk: 1.00%, ATR Mult: 3.00%.

3. **Run with Config:**
   Create a `config.yaml` with `risk_per_trade_pct: 0.5`.

   ```bash
   poetry run run_backtest --pair EURUSD --dataset test --direction LONG --config config.yaml
   ```

   _Expectation:_ Logs show Risk: 0.50%.

4. **Run with Mixed (CLI + Config):**

   ```bash
   poetry run run_backtest --pair EURUSD --dataset test --direction LONG --config config.yaml --risk-pct 2.0
   ```

   _Expectation:_ Logs show Risk: 2.00% (CLI overrides Config).
