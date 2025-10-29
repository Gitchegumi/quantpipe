# Feature Specification: Trend Pullback Continuation Strategy

**Feature Branch**: `001-trend-pullback`
**Created**: 2025-10-25
**Status**: Draft
**Input**: User description: "Design, implement, and validate a parsimonious algorithmic FX trading strategy that trades in the direction of the prevailing trend after a pullback."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Generate Valid Long Trade Signal (Priority: P1)

User wants the system to detect a long trade opportunity aligned with the prevailing uptrend after a controlled pullback.

**Why this priority**: Core value delivery; without a validated entry signal the strategy cannot function.

**Independent Test**: Feed historical OHLCV data where EMA20 > EMA50, include a pullback touching/briefly piercing EMA20, oversold RSI/Stoch RSI, and a bullish reversal candle → system outputs one long signal with structured attributes.

**Acceptance Scenarios**:

1. **Given** EMA20 > EMA50 and no ranging condition, **When** price retraces to EMA20 and RSI(14) < 30, **Then** system marks pullback state but does not yet fire entry until reversal candle confirmed.
2. **Given** prior scenario and next candle forms bullish engulfing pattern while RSI momentum turns upward, **When** evaluation occurs at candle close, **Then** system outputs a LongSignal with fields: timestamp UTC, pair, direction=LONG, entry_price, stop_price, risk_per_trade_pct, rationale tags.
3. **Given** EMA20 repeatedly crosses EMA50 within last N candles, **When** conditions for long otherwise appear, **Then** no signal is emitted (ranging filter active).

---

### User Story 2 - Generate Valid Short Trade Signal (Priority: P2)

User wants the system to detect a short trade opportunity aligned with the prevailing downtrend after a controlled pullback.

**Why this priority**: Completes directional symmetry; enables strategy operation in bearish regimes.

**Independent Test**: Feed OHLCV data where EMA20 < EMA50, include rally back toward EMA20, overbought RSI/Stoch RSI, and bearish reversal candle → system outputs one short signal with structured attributes.

**Acceptance Scenarios**:

1. **Given** EMA20 < EMA50 and stable separation, **When** price rallies to EMA20 and RSI(14) > 70, **Then** system records pullback pending confirmation.
2. **Given** prior scenario and next candle forms bearish engulfing pattern with RSI turning down, **When** evaluation occurs at candle close, **Then** system outputs a ShortSignal with required fields.
3. **Given** EMAs whipsaw crossing (ranging), **When** bearish reversal appears, **Then** system suppresses signal emission.

---

### User Story 3 - Backtest Result Generation (Priority: P3)

User wants to run a historical backtest and obtain standardized performance metrics for the strategy (win rate, average R, Sharpe, max drawdown) to evaluate viability.

**Why this priority**: Enables validation and promotion decisions; required by constitution prior to paper trading.

**Independent Test**: Provide a controlled historical dataset with known synthetic trade opportunities and verify metrics output JSON matches expected derived values.

**Acceptance Scenarios**:

1. **Given** valid historical dataset manifest and parameter set, **When** backtest executes, **Then** system outputs performance report containing required metrics plus trade log with entries/exits.
2. **Given** missing required data file referenced in manifest, **When** backtest starts, **Then** system aborts with structured error referencing missing artifact.
3. **Given** no qualifying signals over dataset, **When** backtest completes, **Then** metrics reflect zero trades and system returns viability flagged as INSUFFICIENT_DATA.

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

- EMA20 and EMA50 diverge then compress rapidly (potential fake ranging) → treat as ranging only if crossings count exceeds RANGE_CROSS_THRESHOLD within last RANGE_LOOKBACK candles.
- ATR extremely low (volatility compression) → minimum stop distance floor applied.
- ATR extremely high (news spike) → strategy suspends new entries for VOLATILITY_SPIKE_COOLDOWN candles.
- Data gap (missing candles) → skip signal evaluation until continuity re-established.
- Reversal candle forms but momentum oscillator not yet turned → defer until both criteria satisfied.
- Multiple signals sequentially within narrow price band → enforce cooldown period COOLDOWN_CANDLES after trade close (see FR-022).
- Price gaps through intended stop at exit evaluation → slippage applied; record adverse excursion.
- Duplicate manifest entry for same pair/timeframe → validation error logged.

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST compute EMA20 and EMA50 for each processed candle and update trend state (UP, DOWN, RANGE).
- **FR-002**: System MUST classify ranging state when EMA cross count ≥ RANGE_CROSS_THRESHOLD within last RANGE_LOOKBACK candles.
- **FR-003**: System MUST detect pullback state when price closes within PULLBACK_DISTANCE_RATIO of fast EMA and momentum oscillator in opposing extreme (RSI < OVERSOLD or RSI > OVERBOUGHT depending on trend).
- **FR-004**: System MUST validate reversal trigger via candle pattern set {bullish_engulfing, bearish_engulfing, pin_bar, strong_close} combined with momentum turn (RSI slope sign change) before signal emission.
- **FR-005**: System MUST output structured trade signal object with fields: id, timestamp_utc, pair, direction, entry_price, initial_stop_price, risk_per_trade_pct, calc_position_size, tags[], version. The id MUST be a deterministic lowercase hex hash of the concatenated string (timestamp_utc|pair|direction|entry_price|strategy_version) using SHA-256 truncated to first 16 characters to ensure reproducibility across identical reruns.
- **FR-006**: System MUST compute initial stop using max(ATR * ATR_STOP_MULT, MIN_STOP_DISTANCE) relative to recent swing point consistent with signal direction.
- **FR-007**: System MUST derive position size from account_equity * risk_per_trade_pct / (entry_price - stop_price adjusted for pip value & lot sizing).
- **FR-008**: System MUST enforce portfolio-level exposure constraints (no more than MAX_OPEN_TRADES or MAX_PAIR_EXPOSURE per pair).
- **FR-009**: System MUST record each executed (simulated) trade in trade log including open timestamp, close timestamp, PnL in R, gross/ net after costs, slippage applied.
- **FR-010**: System MUST apply transaction cost model (spread + slippage + commission if defined) to entry and exit.
- **FR-011**: System MUST support two exit modes: fixed R target (TARGET_R_MULT) OR trailing stop (ATR_TRAIL_MULT) selectable per backtest run.
- **FR-012**: System MUST calculate and output performance metrics: trade_count, win_rate, avg_R, expectancy_R, max_drawdown_R, Sharpe_estimate, profit_factor.
- **FR-013**: System MUST generate data manifest validation report confirming presence, date range coverage, and checksum verification of input candle data.
- **FR-014**: System MUST suspend new signal generation when drawdown exceeds MAX_DRAWDOWN_THRESHOLD until recovery above RECOVERY_LEVEL.
- **FR-015**: System MUST produce reproducibility hash combining parameter set + manifest metadata + strategy version.
- **FR-016**: System SHOULD allow optional higher timeframe filter (ENABLE_HTF_FILTER=true) default false.
- **FR-017**: System MUST log rationale tags (e.g., ["trend", "pullback", "reversal", "risk_ok"]) with each signal for audit.
- **FR-018**: System MUST support time normalization to UTC; input timestamps converted if source differs.
- **FR-019**: System MUST gracefully handle missing candle (skip, mark gap, no signal) without crashing.
- **FR-020**: System MUST expose configuration via parameter dictionary loadable from external configuration files (no hard-coded magic numbers).
- **FR-021**: System MUST ensure that if no qualifying reversal forms within PULLBACK_MAX_AGE candles after pullback detection, the pullback state expires.
- **FR-022**: System MUST apply cooldown of COOLDOWN_CANDLES after trade close before emitting new signal in same direction for same pair.
- **FR-023**: System MUST tag backtest run with run_id and store aggregated metrics separately from per-trade logs.
- **FR-024**: System MUST support dry-run mode emitting signals but skipping trade execution for research.
- **FR-025**: System MUST output structured error when required parameter missing at initialization.
- **FR-026**: When both TARGET_R_MULT and ATR_TRAIL_MULT enabled, system MUST prioritize fixed R exit; if TARGET_R_MULT not reached within EXIT_TARGET_MAX_CANDLES from entry, trailing stop activation supersedes fixed target.
- **FR-027**: System MUST classify volatility regimes using rolling ATR_REGIME_WINDOW candle percentiles: ATR < LOW_PCTL (e.g.,10) => LOW; ATR > HIGH_PCTL (e.g.,90) => HIGH.
- **FR-028**: If ENABLE_HTF_FILTER=true, system MUST require HTF_EMA_FAST > HTF_EMA_SLOW for long signals and HTF_EMA_FAST < HTF_EMA_SLOW for short; otherwise suppress signal.
- **FR-029**: System MUST capture and expose observability metrics each backtest run: candle_processing_latency_ms_p95, avg_entry_slippage_pips, avg_exit_slippage_pips, drawdown_curve (array of timestamp,drawwdown_R), trade_outcome_distribution (win_count, loss_count, avg_win_R, avg_loss_R), and persist them in the run summary. Metrics MUST be derivable deterministically from trade log and timing samples.
- **FR-030**: System MUST ingest historical candle data via streaming chunked processing (chunk size CHUNK_SIZE_CANDLES configurable; default 10_000) maintaining rolling indicator states (EMA, ATR, RSI) without reprocessing earlier candles. Memory footprint for data buffers MUST remain ≤ MEMORY_MAX_BYTES (planning default: 150MB) for 1 year of 1m data on one pair. Strategy MUST flush processed chunks except minimal rolling state to enable multi-year backtests.

### Key Entities *(include if feature involves data)*

- **Candle**: timestamp_utc, open, high, low, close, volume (source-dependent), derived: ema20, ema50, atr, rsi, stoch_rsi.
- **TrendState**: enum {UP, DOWN, RANGE}, fields: cross_count, last_change_timestamp.
- **PullbackState**: active (bool), direction, start_timestamp, qualifying_candle_ids[], oscillator_extreme_flag.
- **TradeSignal**: id, pair, direction, entry_price, stop_price, risk_pct, position_size, tags[], rationale, version.
- **TradeExecution**: signal_id, open_timestamp, close_timestamp, exit_reason {TARGET, TRAILING_STOP, STOP_LOSS, EXPIRY}, pnl_R, slippage, costs.
- **BacktestRun**: run_id, parameters_hash, manifest_ref, metrics_summary, reproducibility_hash.
- **DataManifest**: pair, timeframe, date_range_start, date_range_end, source_provider, checksum, preprocessing_notes.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: Backtest run produces full metrics report in ≤ 2 seconds per 100k candles processed on standard development hardware.
- **SC-002**: Strategy emits ≤ 1 false signal (violating defined criteria) per 10k candles in validation dataset.
- **SC-003**: Reproducibility hash identical across two runs with same manifest & parameters (deterministic output).
- **SC-004**: Drawdown protection halts new signals within one candle after threshold breach 100% of test scenarios.
- **SC-005**: Position sizing error rate (difference from theoretical formula) = 0 across test suite.
- **SC-006**: At least 30 trades generated in core validation dataset (sufficient sample for initial evaluation) OR system flags insufficiency.
- **SC-007**: No strategy crash on malformed/missing candle test dataset; graceful degradation recorded.
- **SC-008**: Performance expectancy (avg_R * win_rate - (1 - win_rate)) remains ≥ -0.2 in baseline sample (avoid obviously unviable configuration).
- **SC-009**: Signal processing latency (95th percentile) ≤ 5ms on standard development hardware for typical timeframe aggregation.
- **SC-010**: Average entry slippage within configured tolerance (default ≤ 1.5 pips) in ≥ 95% of trades.
- **SC-011**: Peak memory usage during backtest of 1 year 1-minute data (single pair) ≤ 150MB.
- **SC-012**: Backtest throughput ≥ 50k candles/second on standard development hardware.

## Assumptions

- Baseline indicator parameters: Fast trend period=20, Slow trend period=50, Momentum oscillator length=14, Volatility period=14.
- Oversold threshold < 30; Overbought threshold > 70 (initial parsimonious defaults).
- Spread/slippage modeled as fixed baseline until dynamic model added.
- Ranging detection: ≥ 3 trend indicator crosses in last 40 candles (initial heuristic).
- Risk per trade default 0.25% of equity.
- Volatility spike cooldown: default = 10 candles (suspend new entries after extreme volatility).
- Trade cooldown: default = 5 candles after trade close.
- Data timezone assumed UTC; adjustment external to strategy module if source differs.
- Manifest guarantees sorted chronological candles.
- Higher timeframe filter disabled initially.
- Min trade sample size for viability = 30 trades.

## Out of Scope

- Live execution & broker integration.
- News and macro event filtering.
- Machine learning optimization or adaptive indicator tuning.
- Multi-strategy portfolio risk aggregation.
- Real-time distributed data ingestion.

## Dependencies & Constraints

- Requires reliable OHLCV historical data source (1m base) aggregated to target timeframes.
- Raw market data stored in `/data/raw/` directory (excluded from version control via .gitignore; see Constitution Principle VI for manifest-based provenance).
- Must conform to constitution risk management and reproducibility standards.
- Restricted to transparent, interpretable indicators (EMA, RSI, ATR) only.
- Memory footprint must support processing at least one year of 1m data per pair in single pass.

## Clarification Resolutions

All previous clarification markers resolved:

- FR-026 exit precedence rule defined with timeout parameter EXIT_TARGET_MAX_CANDLES.
- FR-027 volatility regimes use percentile method with ATR_REGIME_WINDOW, LOW_PCTL, HIGH_PCTL parameters.
- FR-028 higher timeframe filter requires dual EMA alignment.

Remaining parameterization will be finalized in planning phase.

## Clarifications

### Session 2025-10-25

- Q: What uniqueness & reproducibility scheme should TradeSignal id use? → A: Deterministic composite SHA-256 hash of (timestamp_utc|pair|direction|entry_price|strategy_version) truncated to 16 hex chars.
- Q: What observability metrics set should be logged? → A: Trade outcomes + latency per candle + slippage stats + drawdown curve snapshot (FR-029, SC-009, SC-010 added).
- Q: What scalability/data ingestion approach should be used? → A: Streaming chunked ingestion with rolling indicators (FR-030, SC-011, SC-012 added).

## NEXT STEPS

Resolve clarification questions, finalize parameters, proceed to plan and research phase.
