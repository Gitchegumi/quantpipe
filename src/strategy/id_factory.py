"""
Deterministic signal ID generation for trade reproducibility.

This module provides a factory function that generates SHA-256 hash-based
signal IDs from trade parameters. The IDs are deterministic - identical inputs
always produce identical outputs - which enables backtest reproducibility per
Constitution Principle VI.

Signal IDs incorporate:
- Trading pair
- Entry timestamp
- Direction (LONG/SHORT)
- Entry and stop prices
- Position size
- Parameter hash (strategy configuration)
"""

import hashlib
from datetime import datetime


def generate_signal_id(
    pair: str,
    timestamp_utc: datetime,
    direction: str,
    entry_price: float,
    stop_price: float,
    position_size: float,
    parameters_hash: str,
) -> str:
    """
    Generate deterministic SHA-256 hash ID for a trade signal.

    Creates a unique, reproducible identifier by hashing all signal parameters.
    Identical inputs will always produce the same ID, ensuring backtest
    reproducibility across runs.

    The ID incorporates:
    - Trading pair (e.g., "EURUSD")
    - Entry timestamp (ISO 8601 format)
    - Trade direction ("LONG" or "SHORT")
    - Entry price (6 decimal precision)
    - Stop price (6 decimal precision)
    - Position size (6 decimal precision)
    - Strategy parameters hash (SHA-256)

    Args:
        pair: Trading pair symbol (e.g., "EURUSD", "GBPUSD").
        timestamp_utc: UTC timestamp when signal was generated.
        direction: Trade direction ("LONG" or "SHORT").
        entry_price: Proposed entry price.
        stop_price: Proposed stop-loss price.
        position_size: Position size in lots.
        parameters_hash: SHA-256 hash of strategy parameters.

    Returns:
        64-character hexadecimal SHA-256 hash string.

    Examples:
        >>> from datetime import datetime, timezone
        >>> signal_id = generate_signal_id(
        ...     pair="EURUSD",
        ...     timestamp_utc=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ...     direction="LONG",
        ...     entry_price=1.10000,
        ...     stop_price=1.09800,
        ...     position_size=0.01,
        ...     parameters_hash="a1b2c3d4e5f6..."
        ... )
        >>> len(signal_id)
        64
        >>> signal_id[:8]  # First 8 characters (example)
        'f4a5b6c7'

        >>> # Identical inputs produce identical IDs
        >>> signal_id2 = generate_signal_id(
        ...     pair="EURUSD",
        ...     timestamp_utc=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        ...     direction="LONG",
        ...     entry_price=1.10000,
        ...     stop_price=1.09800,
        ...     position_size=0.01,
        ...     parameters_hash="a1b2c3d4e5f6..."
        ... )
        >>> signal_id == signal_id2
        True
    """
    # Format timestamp as ISO 8601 with microsecond precision
    timestamp_str = timestamp_utc.isoformat()

    # Format prices and position size with fixed precision
    entry_str = f"{entry_price:.6f}"
    stop_str = f"{stop_price:.6f}"
    size_str = f"{position_size:.6f}"

    # Construct deterministic input string
    components = [
        pair,
        timestamp_str,
        direction,
        entry_str,
        stop_str,
        size_str,
        parameters_hash,
    ]
    input_string = "|".join(components)

    # Compute SHA-256 hash
    sha256 = hashlib.sha256()
    sha256.update(input_string.encode("utf-8"))
    signal_id = sha256.hexdigest()

    return signal_id


def compute_parameters_hash(parameters_dict: dict) -> str:
    """
    Compute deterministic SHA-256 hash of strategy parameters.

    Creates a reproducible hash from a dictionary of strategy parameters.
    Parameter keys are sorted alphabetically before hashing to ensure
    determinism regardless of dict ordering.

    Args:
        parameters_dict: Dictionary of strategy parameters.

    Returns:
        64-character hexadecimal SHA-256 hash string.

    Examples:
        >>> params = {
        ...     "ema_fast": 20,
        ...     "ema_slow": 50,
        ...     "rsi_period": 14,
        ...     "position_risk_pct": 0.25
        ... }
        >>> params_hash = compute_parameters_hash(params)
        >>> len(params_hash)
        64

        >>> # Order doesn't matter - same hash
        >>> params2 = {
        ...     "position_risk_pct": 0.25,
        ...     "rsi_period": 14,
        ...     "ema_slow": 50,
        ...     "ema_fast": 20
        ... }
        >>> compute_parameters_hash(params2) == params_hash
        True
    """
    # Sort parameters by key for determinism
    sorted_items = sorted(parameters_dict.items())

    # Convert to string representation
    param_str = "|".join(f"{k}={v}" for k, v in sorted_items)

    # Compute SHA-256 hash
    sha256 = hashlib.sha256()
    sha256.update(param_str.encode("utf-8"))
    params_hash = sha256.hexdigest()

    return params_hash
