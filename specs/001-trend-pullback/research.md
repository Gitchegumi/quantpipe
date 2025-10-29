# Research: Trend Pullback Continuation Strategy

**Date**: 2025-10-25
**Branch**: 001-trend-pullback

## Decisions & Rationale

### Indicator Set

- **Decision**: Use EMA20, EMA50, RSI(14), ATR(14); optional Stoch RSI deferred.
- **Rationale**: Minimal interpretable set captures trend, momentum exhaustion, volatility.
- **Alternatives Considered**: MACD (redundant with EMAs), Bollinger Bands (added complexity), Stoch RSI (may be added later for refinement).

### Trend Definition

- **Decision**: EMA20 > EMA50 => UP, EMA20 < EMA50 => DOWN; RANGE if cross count ≥3 over last 40 candles.
- **Rationale**: Simple, robust; prevents overtrading in chop.
- **Alternatives**: ADX threshold (requires extra tuning), multi-timeframe trend alignment (adds complexity early).

### Pullback Qualification

- **Decision**: Close within configurable ratio distance of EMA20 AND oscillator extreme (RSI <30 or >70) sets pullback state.
- **Rationale**: Ensures mean-reversion phase before reversal attempt.
- **Alternatives**: Price retrace % of ATR; Fibs (less parsimonious).

### Reversal Confirmation

- **Decision**: Candle pattern (engulfing, pin, strong close) + RSI slope change.
- **Rationale**: Combines price action + momentum normalization.
- **Alternatives**: Pattern-only (higher false positives), oscillator crossover (lagging).

### Stop Placement

- **Decision**: max(ATR*ATR_STOP_MULT, MIN_STOP_DISTANCE) from swing point.
- **Rationale**: Adapts to volatility while enforcing floor.
- **Alternatives**: Fixed pip distance (ignores volatility), fractal-based stops (higher complexity).

### Position Sizing

- **Decision**: Risk % of equity / (entry - stop) adjusted by pip value and lot size.
- **Rationale**: Standard risk model; scales naturally.
- **Alternatives**: Kelly fraction (volatile), volatility parity (overkill single strategy).

### Exit Logic Precedence

- **Decision**: Fixed R takes precedence; trailing activates after timeout (EXIT_TARGET_MAX_CANDLES) if target not hit.
- **Rationale**: Avoid premature trailing; allows capturing structured reward.
- **Alternatives**: First-hit exit (could truncate large trends), always trail (reduces discrete expectancy clarity).

### Volatility Regimes

- **Decision**: Percentile-based (LOW_PCTL/HIGH_PCTL) over rolling ATR_REGIME_WINDOW.
- **Rationale**: Adaptive to instrument specifics.
- **Alternatives**: Static multipliers (less adaptive), z-score (sensitive to distribution shifts).

### Higher Timeframe Filter

- **Decision**: Dual EMA alignment required when enabled (HTF_EMA_FAST > HTF_EMA_SLOW for longs).
- **Rationale**: Reduces false signals in countertrend noise.
- **Alternatives**: Price above HTF EMA only (weaker filter), HTF ADX (extra indicator complexity).

### Data Ingestion & Scalability

- **Decision**: Streaming chunks of CHUNK_SIZE_CANDLES (default 10k), retain only rolling state.
- **Rationale**: Memory efficiency, supports multi-year datasets.
- **Alternatives**: Full in-memory (risk OOM), lazy fetch per indicator (I/O overhead).

### Observability Metrics

- **Decision**: candle_processing_latency_ms_p95, slippage stats, drawdown curve, trade outcome distribution.
- **Rationale**: Balances insight and simplicity.
- **Alternatives**: Deep per-indicator telemetry (overhead), minimal PnL only (insufficient diagnostics).

### Deterministic Signal IDs

- **Decision**: SHA-256 hash of (timestamp|pair|direction|entry_price|strategy_version) truncated 16 hex.
- **Rationale**: Reproducible diffing across reruns.
- **Alternatives**: UUID (non-deterministic), sequential counters (not portable).

## Parameter Defaults (Initial)

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| EMA_FAST | 20 | Common short-term trend lens |
| EMA_SLOW | 50 | Medium-term trend baseline |
| RSI_LEN | 14 | Standard momentum length |
| ATR_LEN | 14 | Industry standard volatility window |
| RANGE_CROSS_THRESHOLD | 3 | Prevent churn trading |
| RANGE_LOOKBACK | 40 | Captures recent regime |
| PULLBACK_DISTANCE_RATIO | 0.005 | ~0.5% proximity to EMA (tunable) |
| OVERSOLD | 30 | Conventional threshold |
| OVERBOUGHT | 70 | Conventional threshold |
| ATR_STOP_MULT | 1.5 | Balance noise vs protection |
| MIN_STOP_DISTANCE | 0.0008 | Avoid ultra-tight stops (example for EURUSD) |
| TARGET_R_MULT | 2.0 | Baseline risk/reward |
| ATR_TRAIL_MULT | 2.0 | Reactive trailing distance |
| EXIT_TARGET_MAX_CANDLES | 25 | Give trade time to reach target |
| LOW_PCTL | 10 | Volatility compression threshold |
| HIGH_PCTL | 90 | Elevated volatility threshold |
| ATR_REGIME_WINDOW | 200 | Sufficient statistical window |
| CHUNK_SIZE_CANDLES | 10000 | Tradeoff throughput vs memory |
| SLIPPAGE_TOLERANCE_PIPS | 1.5 | Performance expectation |
| MAX_OPEN_TRADES | 3 | Initial portfolio risk cap |
| MAX_PAIR_EXPOSURE | 2 | Avoid concentration |
| MAX_DRAWDOWN_THRESHOLD | -10R | Halt protection |
| RECOVERY_LEVEL | -7R | Resume threshold |
| COOLDOWN_CANDLES | 5 | Prevent clustering |
| PULLBACK_MAX_AGE | 15 | Avoid stale setups |

## Unresolved Items

None (all previous clarifications resolved). Further tuning deferred to optimization phase after baseline backtest.

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Overfitting on small dataset | False confidence | Minimum trade count criterion (SC-006); walk-forward planned Phase 2 |
| Latency spikes due to Python overhead | Slower throughput | Vectorized indicator math; pre-allocate arrays; optional numba later |
| Data gaps causing mis-signals | Incorrect entries | Gap detection skip logic (edge cases section) |
| Volatility regime misclassification early | Poor stop sizing | Use percentile with rolling recalibration per dataset |
| Parameter drift across experiments | Reproducibility loss | Repro hash + manifest linkage |

## Future Considerations

- Walk-forward validation and significance testing integration.
- Extension to multi-pair portfolio risk correlation logic.
- Live monitoring adapter using same observability metrics.

## Conclusion

Foundational research complete; proceed to design artifacts (data model, contracts, quickstart) and implementation planning.
