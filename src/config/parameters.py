"""
Strategy parameter configuration using Pydantic.

This module provides type-safe parameter validation and loading for the
trend pullback continuation strategy.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class StrategyParameters(BaseModel):
    """
    Configuration parameters for the trend pullback continuation strategy.
    
    All parameters use conservative defaults suitable for FX trading on
    1-minute to 1-hour timeframes. Parameters are validated at initialization
    to ensure values are within acceptable ranges.
    
    Attributes:
        ema_fast: Fast exponential moving average period (default: 20).
        ema_slow: Slow exponential moving average period (default: 50).
        rsi_length: RSI momentum oscillator period (default: 14).
        atr_length: Average True Range volatility period (default: 14).
        oversold_threshold: RSI level indicating oversold condition (default: 30).
        overbought_threshold: RSI level indicating overbought condition (default: 70).
        pullback_distance_ratio: Maximum distance from fast EMA as ratio of ATR (default: 1.5).
        range_cross_threshold: Number of EMA crosses to classify ranging market (default: 3).
        range_lookback: Candles to look back for range detection (default: 40).
        atr_stop_mult: ATR multiplier for initial stop distance (default: 2.0).
        min_stop_distance: Minimum stop distance in pips (default: 10.0).
        target_r_mult: Target profit as multiple of risk R (default: 2.0).
        atr_trail_mult: ATR multiplier for trailing stop (default: 3.0).
        exit_target_max_candles: Max candles before switching from fixed target to trailing
         (default: 50).
        risk_per_trade_pct: Risk per trade as percentage of equity (default: 0.25).
        max_open_trades: Maximum concurrent open positions (default: 3).
        max_pair_exposure: Maximum exposure per currency pair (default: 1).
        max_drawdown_threshold: Maximum drawdown before halting (default: 0.10).
        recovery_level: Drawdown recovery threshold to resume (default: 0.05).
        volatility_spike_cooldown: Candles to wait after volatility spike (default: 10).
        cooldown_candles: Candles to wait after trade close (default: 5).
        pullback_max_age: Maximum candles pullback can persist before expiry (default: 15).
        chunk_size_candles: Candles per processing chunk for streaming (default: 10000).
        memory_max_bytes: Maximum memory for data buffers in bytes (default: 157286400).
        enable_htf_filter: Enable higher timeframe filter (default: False).
        htf_ema_fast: HTF fast EMA period (default: 20).
        htf_ema_slow: HTF slow EMA period (default: 50).
        atr_regime_window: Window for ATR regime classification (default: 100).
        low_volatility_percentile: Percentile threshold for low volatility (default: 10).
        high_volatility_percentile: Percentile threshold for high volatility (default: 90).
    """
    
    # Trend indicators
    ema_fast: int = Field(default=20, gt=0, le=200)
    ema_slow: int = Field(default=50, gt=0, le=500)
    
    # Momentum and volatility
    rsi_length: int = Field(default=14, gt=0, le=100)
    atr_length: int = Field(default=14, gt=0, le=100)
    
    # Pullback detection
    oversold_threshold: float = Field(default=30.0, ge=0.0, le=50.0)
    overbought_threshold: float = Field(default=70.0, ge=50.0, le=100.0)
    pullback_distance_ratio: float = Field(default=1.5, gt=0.0, le=5.0)
    
    # Ranging market filter
    range_cross_threshold: int = Field(default=3, gt=0, le=10)
    range_lookback: int = Field(default=40, gt=0, le=200)
    
    # Risk management
    atr_stop_mult: float = Field(default=2.0, gt=0.0, le=10.0)
    min_stop_distance: float = Field(default=10.0, gt=0.0)
    target_r_mult: float = Field(default=2.0, gt=0.0, le=20.0)
    atr_trail_mult: float = Field(default=3.0, gt=0.0, le=20.0)
    exit_target_max_candles: int = Field(default=50, gt=0, le=500)
    risk_per_trade_pct: float = Field(default=0.25, gt=0.0, le=5.0)
    max_open_trades: int = Field(default=3, gt=0, le=20)
    max_pair_exposure: int = Field(default=1, gt=0, le=10)
    max_drawdown_threshold: float = Field(default=0.10, gt=0.0, le=0.50)
    recovery_level: float = Field(default=0.05, gt=0.0, le=0.50)
    
    # Cooldown and expiry
    volatility_spike_cooldown: int = Field(default=10, ge=0, le=100)
    cooldown_candles: int = Field(default=5, ge=0, le=100)
    pullback_max_age: int = Field(default=15, gt=0, le=100)
    
    # Performance and streaming
    chunk_size_candles: int = Field(default=10000, gt=0)
    memory_max_bytes: int = Field(default=157286400, gt=0)  # 150MB
    
    # Higher timeframe filter
    enable_htf_filter: bool = Field(default=False)
    htf_ema_fast: int = Field(default=20, gt=0, le=200)
    htf_ema_slow: int = Field(default=50, gt=0, le=500)
    
    # Volatility regime
    atr_regime_window: int = Field(default=100, gt=0, le=1000)
    low_volatility_percentile: float = Field(default=10.0, ge=0.0, le=50.0)
    high_volatility_percentile: float = Field(default=90.0, ge=50.0, le=100.0)
    
    @field_validator('ema_slow')
    @classmethod
    def slow_must_exceed_fast(cls, v, info):
        """Validate that slow EMA period exceeds fast EMA period."""
        if 'ema_fast' in info.data and v <= info.data['ema_fast']:
            raise ValueError('ema_slow must be greater than ema_fast')
        return v
    
    @field_validator('overbought_threshold')
    @classmethod
    def overbought_must_exceed_oversold(cls, v, info):
        """Validate that overbought threshold exceeds oversold threshold."""
        if 'oversold_threshold' in info.data and v <= info.data['oversold_threshold']:
            raise ValueError('overbought_threshold must be greater than oversold_threshold')
        return v
    
    @field_validator('recovery_level')
    @classmethod
    def recovery_must_be_less_than_drawdown(cls, v, info):
        """Validate that recovery level is less than drawdown threshold."""
        if 'max_drawdown_threshold' in info.data and v >= info.data['max_drawdown_threshold']:
            raise ValueError('recovery_level must be less than max_drawdown_threshold')
        return v
    
    @field_validator('htf_ema_slow')
    @classmethod
    def htf_slow_must_exceed_htf_fast(cls, v, info):
        """Validate that HTF slow EMA period exceeds HTF fast EMA period."""
        if 'htf_ema_fast' in info.data and v <= info.data['htf_ema_fast']:
            raise ValueError('htf_ema_slow must be greater than htf_ema_fast')
        return v
    
    @field_validator('high_volatility_percentile')
    @classmethod
    def high_vol_must_exceed_low_vol(cls, v, info):
        """Validate that high volatility percentile exceeds low volatility percentile."""
        if 'low_volatility_percentile' in info.data and v <= info.data['low_volatility_percentile']:
            raise ValueError('high_volatility_percentile must be greater than low_volatility_percentile')
        return v


def load_parameters(config_dict: dict | None = None) -> StrategyParameters:
    """
    Load and validate strategy parameters from a configuration dictionary.
    
    Args:
        config_dict: Optional dictionary of parameter overrides. If None,
            default values are used.
    
    Returns:
        Validated StrategyParameters instance.
    
    Raises:
        ValidationError: If any parameter values are invalid.
    
    Examples:
        >>> params = load_parameters()  # Use defaults
        >>> params.ema_fast
        20
        
        >>> custom_params = load_parameters({"ema_fast": 10, "ema_slow": 30})
        >>> custom_params.ema_fast
        10
    """
    if config_dict is None:
        config_dict = {}
    return StrategyParameters(**config_dict)
