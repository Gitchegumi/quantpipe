import polars as pl
import numpy as np
from typing import Optional

def calculate_adx(
    high: pl.Series, 
    low: pl.Series, 
    close: pl.Series, 
    period: int = 14
) -> pl.Series:
    """
    Calculate Average Directional Index (ADX).
    ADX > 25: Strong Trend
    ADX < 20: Weak/No Trend
    """
    # Use polars expressions for efficiency
    plus_dm = (high - high.shift(1)).map_elements(lambda x: max(x, 0), return_dtype=pl.Float64).fill_null(0)
    minus_dm = (low.shift(1) - low).map_elements(lambda x: max(x, 0), return_dtype=pl.Float64).fill_null(0)
    
    # Logic: if plus_dm > minus_dm, plus_dm = plus_dm else 0
    # Actually simpler:
    plus_dm = pl.when(plus_dm > minus_dm).then(plus_dm).otherwise(0)
    minus_dm = pl.when(minus_dm > plus_dm).then(minus_dm).otherwise(0)
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pl.max_horizontal(tr1, tr2, tr3)
    
    atr = tr.rolling_mean(window_size=period)
    plus_di = 100 * (plus_dm.rolling_mean(window_size=period) / atr)
    minus_di = 100 * (minus_dm.rolling_mean(window_size=period) / atr)
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling_mean(window_size=period)
    
    return adx

def calculate_hurst_exponent(series: pl.Series, max_lag: int = 20) -> float:
    """
    Estimate Hurst Exponent using Rescaled Range (R/S) analysis.
    H < 0.5: Mean Reverting
    H = 0.5: Random Walk
    H > 0.5: Trending
    """
    # Simple implementation for vectorized backtesting context
    # Usually requires multiple window sizes; this is a simplified log-variance version
    if len(series) < max_lag * 2:
        return 0.5
        
    lags = range(2, max_lag)
    tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
    
    # Regression to find the Hurst exponent
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0
