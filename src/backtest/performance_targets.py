"""Performance target constants for scan and simulation benchmarking.

This module defines the performance thresholds and target metrics used to validate
the optimized scan and simulation implementation against baseline measurements.

All constants are derived from the specification requirements (Spec 010).
"""

# Scan Performance Targets
SCAN_MAX_SECONDS = 720  # 12 minutes for 6.9M candles
SCAN_MIN_SPEEDUP_PCT = 50  # Minimum 50% time reduction vs baseline

# Simulation Performance Targets
SIM_MAX_SECONDS = 480  # 8 minutes for ~84,938 trades
SIM_MIN_SPEEDUP_PCT = 55  # Minimum 55% time reduction vs baseline

# Memory Performance Targets
MEM_PEAK_REDUCTION_TARGET_PCT = 30  # Minimum 30% peak memory reduction
MEM_ALLOCATION_REDUCTION_TARGET_PCT = 70  # Minimum 70% allocation reduction
ALLOCATION_REDUCTION_TARGET_PCT = 70  # Alias for allocation reduction target

# Progress Emission Targets
PROGRESS_MAX_INTERVAL_SECONDS = 120  # Maximum 2 minutes between updates
PROGRESS_MAX_PERCENT_DRIFT = 2.0  # Maximum 2% increment between updates
PROGRESS_MAX_OVERHEAD_PCT = 1.0  # Progress overhead must be ≤1% of total time
PROGRESS_OVERHEAD_TARGET_PCT = 1.0  # Alias for progress overhead target

# Determinism Targets
DETERMINISTIC_TIMING_VARIANCE_PCT = 1.0  # ±1% timing variance across runs
DETERMINISTIC_PNL_VARIANCE_PCT = 0.5  # ±0.5% PnL variance for equivalence

# Polars Performance Targets
POLARS_MIN_SPEEDUP_PCT = 20  # Minimum 20% preprocessing speedup vs pandas
POLARS_MIN_MEM_REDUCTION_PCT = 15  # Minimum 15% memory reduction vs pandas

# Numba Adoption Criteria (optional, deferred)
NUMBA_MIN_SPEEDUP_PCT = 25  # Adopt only if ≥25% additional speedup
NUMBA_HOTSPOT_THRESHOLD_PCT = 40  # Inner loop must be ≥40% of total runtime

# Progress Emission Configuration
PROGRESS_STRIDE_ITEMS = 16384  # Emit progress every 2^14 items (16K)
PROGRESS_TIME_FALLBACK_SEC = 120  # Emit if >120s elapsed since last update

# Equivalence Testing Tolerances
EQUIVALENCE_SIGNAL_COUNT_EXACT = True  # Signal counts must match exactly
EQUIVALENCE_TRADE_COUNT_EXACT = True  # Trade counts must match exactly
EQUIVALENCE_PNL_TOLERANCE_PCT = 0.5  # PnL variance ≤0.5% for equivalence pass

# Dataset Scale Reference (6.9M candles baseline)
REFERENCE_CANDLE_COUNT = 6_900_000
REFERENCE_TRADE_COUNT = 84_938
