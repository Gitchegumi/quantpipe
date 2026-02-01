# Private Strategies

This directory is for proprietary or experimental trading strategies that should **not** be committed to the public open-source repository.

## Setup

1. Create a python module here (e.g., `my_secret_alpha.py`).
2. Implement your strategy class (must inherit from `BaseStrategy` or implement the protocol).
3. Expose a `run` or `execute` function.

## Running

You can run these strategies using the CLI by pointing to the module path. Since this folder is in the root, you may need to run it as a module or ensure it's in the python path.

Example:
```bash
# Assuming you are in the repo root
python -m src.cli.main backtest --strategy-module private_strategies.my_secret_alpha --register-strategy SecretStrat1 --data ...
```

## Structure

```
private_strategies/
├── __init__.py
├── README.md
├── alpha_v1/
│   ├── __init__.py
│   └── strategy.py
└── experimental.py
```
