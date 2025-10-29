"""
Custom exception classes for the trading strategy.

This module defines domain-specific exceptions that provide clear error
semantics for different failure modes in the trading system.

All exceptions include descriptive messages and optional context data to
aid in debugging and error handling.
"""


class DataIntegrityError(Exception):
    """
    Raised when data validation or integrity checks fail.

    This exception indicates issues with market data quality, such as:
    - Missing required candles (timestamp gaps)
    - Invalid OHLC relationships (e.g., high < low)
    - Checksum verification failures
    - Manifest validation errors

    Attributes:
        message: Human-readable error description.
        context: Optional dictionary with additional error context.

    Examples:
        >>> raise DataIntegrityError(
        ...     "Candle timestamp gap detected",
        ...     context={"expected": "2025-01-01 12:00", "actual": "2025-01-01 13:00"}
        ... )
        Traceback (most recent call last):
        ...
        DataIntegrityError: Candle timestamp gap detected
    """

    def __init__(self, message: str, context: dict | None = None):
        """
        Initialize DataIntegrityError.

        Args:
            message: Error description.
            context: Optional dictionary with error details.
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class RiskLimitError(Exception):
    """
    Raised when risk management constraints are violated.

    This exception indicates attempts to exceed defined risk limits, such as:
    - Maximum drawdown threshold breached
    - Position size exceeds maximum allowed
    - Too many concurrent open trades
    - Insufficient account equity for trade

    Attributes:
        message: Human-readable error description.
        limit_type: Type of limit violated (e.g., 'drawdown', 'position_size').
        current_value: Current value that violated the limit.
        limit_value: Maximum allowed value.

    Examples:
        >>> raise RiskLimitError(
        ...     "Maximum drawdown exceeded",
        ...     limit_type="drawdown",
        ...     current_value=0.15,
        ...     limit_value=0.10
        ... )
        Traceback (most recent call last):
        ...
        RiskLimitError: Maximum drawdown exceeded (limit: 0.1, current: 0.15)
    """

    def __init__(
        self,
        message: str,
        limit_type: str | None = None,
        current_value: float | None = None,
        limit_value: float | None = None,
    ):
        """
        Initialize RiskLimitError.

        Args:
            message: Error description.
            limit_type: Type of limit violated.
            current_value: Actual value that exceeded the limit.
            limit_value: Maximum allowed value.
        """
        super().__init__(message)
        self.message = message
        self.limit_type = limit_type
        self.current_value = current_value
        self.limit_value = limit_value

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.limit_value is not None and self.current_value is not None:
            return (
                f"{self.message} "
                f"(limit: {self.limit_value}, current: {self.current_value})"
            )
        return self.message


class ExecutionSimulationError(Exception):
    """
    Raised when trade execution simulation encounters an error.

    This exception indicates problems during backtesting execution, such as:
    - Invalid trade state transitions
    - Price slippage calculation failures
    - Missing required execution parameters
    - Inconsistent entry/exit timestamps

    Attributes:
        message: Human-readable error description.
        signal_id: ID of the signal that caused the error (if applicable).
        stage: Execution stage where error occurred (e.g., 'entry', 'exit').

    Examples:
        >>> raise ExecutionSimulationError(
        ...     "Invalid exit price",
        ...     signal_id="a1b2c3d4e5f6g7h8",
        ...     stage="exit"
        ... )
        Traceback (most recent call last):
        ...
        ExecutionSimulationError: Invalid exit price [signal: a1b2c3d4e5f6g7h8, stage: exit]
    """

    def __init__(
        self,
        message: str,
        signal_id: str | None = None,
        stage: str | None = None,
    ):
        """
        Initialize ExecutionSimulationError.

        Args:
            message: Error description.
            signal_id: ID of the signal being executed.
            stage: Execution stage ('entry', 'exit', 'validation').
        """
        super().__init__(message)
        self.message = message
        self.signal_id = signal_id
        self.stage = stage

    def __str__(self) -> str:
        """Return string representation of the error."""
        parts = [self.message]
        if self.signal_id:
            parts.append(f"signal: {self.signal_id}")
        if self.stage:
            parts.append(f"stage: {self.stage}")

        if len(parts) > 1:
            context = ", ".join(parts[1:])
            return f"{parts[0]} [{context}]"
        return parts[0]
