# Feature Specification: Decouple Strategy Logic from Risk Management

**Feature Branch**: `021-decouple-risk-management`
**Created**: 2024-12-24
**Status**: Draft
**Input**: GitHub Issue #12 - Separate trade signal generation from risk management/execution

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Change Risk Policy Without Code Modification (Priority: P1)

A trader wants to switch from a fixed 3:1 reward-to-risk ratio to an ATR-based trailing stop without modifying any strategy code. They update their configuration file or CLI arguments and re-run the backtest.

**Why this priority**: This is the core value proposition—enabling runtime risk policy changes without touching strategy modules prevents bugs and speeds iteration.

**Independent Test**: Can be fully validated by running the same strategy with two different risk configs and confirming different order outcomes from identical signals.

**Acceptance Scenarios**:

1. **Given** a strategy that produces LONG signals, **When** I configure `--tp-policy RiskMultiple --rr 3.0`, **Then** take-profit orders are placed at 3× the stop distance above entry.
2. **Given** a strategy that produces LONG signals, **When** I configure `--stop-policy ATR_Trailing --atr-mult 2.0`, **Then** stop orders trail using 2× ATR rather than being fixed.
3. **Given** identical market data and strategy parameters, **When** I change only the risk config, **Then** trade outcomes differ only in SL/TP placement and position sizing.

---

### User Story 2 - Position Sizing by Risk Percent (Priority: P1)

A trader wants to risk exactly 0.25% of their portfolio on each trade, regardless of the volatility (ATR) or price level. The system calculates position size automatically based on the stop distance.

**Why this priority**: Position sizing is fundamental to risk management and required for both fixed and trailing policies.

**Independent Test**: Validate position size calculation matches `(account_balance × risk_pct) / (stop_distance × pip_value)`.

**Acceptance Scenarios**:

1. **Given** $10,000 balance and 0.25% risk per trade, **When** stop distance is 20 pips, **Then** position size is 0.125 lots (assuming $10/pip standard lot).
2. **Given** varying stop distances across trades, **When** risk percent is constant, **Then** position sizes adjust inversely to stop distance.
3. **Given** position size exceeds max allowed, **When** order is built, **Then** position is capped at max and a warning is logged.

---

### User Story 3 - Trailing Stop Updates on Each Bar (Priority: P2)

A trader uses an ATR-based trailing stop that moves favorable as price moves in their direction. On each new bar, the system recalculates the stop and updates it if the new level is more favorable.

**Why this priority**: Trailing stops enable capturing extended trends while locking in profits—a key risk policy variant.

**Independent Test**: Run backtest simulation, verify stop price updates on consecutive bars as price moves favorably.

**Acceptance Scenarios**:

1. **Given** a LONG position with ATR trailing stop, **When** price moves up significant enough, **Then** stop moves up to `high - (ATR × multiplier)`.
2. **Given** a LONG position with ATR trailing stop, **When** price moves down, **Then** stop does not move lower (only ratchets up).
3. **Given** price hits the trailed stop, **When** order is filled, **Then** exit reason is recorded as "trailing_stop_hit".

---

### User Story 4 - Multiple Risk Policies Available at Launch (Priority: P2)

The system ships with at least two working policies: Fixed Ratio (e.g., 3:1 TP:SL) and Trailing Stop (e.g., ATR-based). Additional policies can be added without modifying existing code.

**Why this priority**: Demonstrates the pluggable architecture and provides immediate value to users with different trading styles.

**Independent Test**: Backtest same strategy with each policy, confirm both run without error and produce distinct trade lifecycles.

**Acceptance Scenarios**:

1. **Given** `FixedRatio` policy selected, **When** trade exits, **Then** exit is at either fixed TP or fixed SL.
2. **Given** `Trailing` policy selected, **When** trade exits, **Then** exit may occur at a stop level different from initial SL.
3. **Given** a new policy class is created, **When** registered in config, **Then** it can be selected without modifying engine code.

---

### Edge Cases

- What happens when stop distance calculates to zero (entry == stop)?
  - System returns minimum position size and logs warning.
- What happens when signal direction is invalid (not LONG/SHORT)?
  - Validation error raised before order building.
- What happens when ATR value is missing for ATR-based policies?
  - Raise `RiskConfigurationError` before order building.
- What happens when portfolio balance is zero or negative?
  - Position sizing rejects trade with validation error.
- What happens when market gaps past stop level?
  - Exit triggered at first available price (simulated slippage).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: Strategies MUST emit signals containing only: direction (LONG/SHORT), symbol, and optional entry price hint. Signals MUST NOT contain stop-loss, take-profit, or position size.
- **FR-002**: A RiskManager component MUST accept signals and portfolio state, returning an OrderPlan with concrete entry, stop-loss, take-profit orders, and position size.
- **FR-003**: RiskManager MUST compose pluggable StopPolicy, TakeProfitPolicy, and PositionSizer components.
- **FR-004**: System MUST support runtime selection of risk policy via configuration file (JSON) or CLI arguments.
- **FR-005**: Position sizing MUST use the formula: `risk_amount / (stop_distance_pips × pip_value)`, respecting min/max limits.
- **FR-006**: Trailing stop policies MUST ratchet stops in favorable direction only (never widen risk).
- **FR-007**: Backtest logs MUST include `{strategy_name, risk_manager_type, risk_params}` for reproducibility labeling.
- **FR-008**: System MUST provide at least two stop policies at launch: fixed ATR-based and ATR-trailing.
- **FR-009**: System MUST provide at least two take-profit policies at launch: fixed R-multiple and None (no TP).
- **FR-010**: Existing strategies MUST continue working with a default risk config that matches current behavior (backward compatibility).

### Key Entities

- **Signal**: Direction, symbol, timestamp, optional entry hint. No risk/money data.
- **OrderPlan**: Complete set of orders (entry, SL, TP) with position size and trailing rules.
- **RiskManager**: Orchestrator composing policies and sizers.
- **StopPolicy**: Calculates initial and updated stop prices.
- **TakeProfitPolicy**: Calculates take-profit targets (or None for trail-only).
- **PositionSizer**: Calculates position size from risk parameters.
- **RiskConfig**: Configuration object defining selected policies and parameters.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Same strategy signal produces different order plans under different risk configs—verified by unit tests.
- **SC-002**: Users can switch between Fixed Ratio and Trailing Stop policies via config/CLI without code changes—verified by integration test.
- **SC-003**: Strategy modules contain zero imports from risk/sizing modules—verified by static analysis (grep or import inspection).
- **SC-004**: All existing backtests produce identical results when using default risk config that matches legacy behavior—verified by regression test.
- **SC-005**: Backtest run metadata includes risk manager type and parameters—verified by log/output inspection.
- **SC-006**: Unit test coverage for position sizing edge cases (zero stop, max cap, JPY pairs) reaches 100% of identified branches.

## Assumptions

- JSON configuration format is acceptable for risk policy selection (can extend to YAML later).
- ATR indicator values are available in candle data for ATR-based policies.
- Single-entry orders (no scale-in/partial entry) are the scope for initial implementation.
- Trailing stop updates occur at bar close, not intra-bar (backtesting context).
- Default risk behavior matches current system: 0.25% risk, 2× ATR stop, 2:1 TP (or as currently configured).
