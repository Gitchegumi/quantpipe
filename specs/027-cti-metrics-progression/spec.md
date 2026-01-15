# Feature Specification: CTI Progression & Advanced Metrics

**Feature Branch**: `027-cti-metrics-progression`
**Created**: 2026-01-14
**Status**: Draft
**Input**: Combine Issue #24 (City Traders Imperium Progression) and #60 (Advanced Backtest Metrics)
**Reference**: [City Traders Imperium Scaling Plan](https://citytradersimperium.com/funding-programmes/)

## User Scenarios & Testing

### User Story 1 - Advanced Statistical Metrics (Priority: P1)

Quant developers need comprehensive performance metrics to evaluate strategies effectively. The current output is minimal. This story adds institutional-grade metrics to the backtest reports.

**Why this priority**: Metrics are the foundation for any strategy evaluation. Without them, users cannot assess the viability of strategies, including those needed for CTI challenge rules.

**Independent Test**: Run any backtest and verify the new metrics appear in the JSON/text output.

**Acceptance Scenarios**:

1. **Given** a completed backtest, **When** results are generated, **Then** the output includes "Average Trade Duration", "Risk-to-Reward Ratio", "Sharpe Ratio", "Sortino Ratio", "Profit Factor", "Win Rate", and "Expectancy".
2. **Given** a winning/losing streak, **When** calculated, **Then** the "Max Consecutive Wins" and "Max Consecutive Losses" metrics accurately reflect the sequence.
3. **Given** a strategy name is provided, **When** reporting, **Then** the "Strategy Name" is clearly labeled.

---

### User Story 2 - CTI Challenge Rules Enforcement (Priority: P1)

Traders need to verify compliance with City Traders Imperium (CTI) programs: **1-Step Challenge**, **2-Step Challenge**, and **Instant Funding**. Each has specific start balances, profit targets, and drawdown limits.

**Why this priority**: Core requirement for users targeting CTI funding.

**Independent Test**: Run backtests with standard CTI presets (e.g., "1-Step 10k") and verify "Pass/Fail" results match the rules (e.g., fail if daily drawdown > 5% or trailing > 5%).

**Acceptance Scenarios**:

1. **Given** a 1-Step Challenge backtest, **When** profit reaches 8% without passing passing 5% trailing drawdown, **Then** status is "PASSED" (Phase 1 complete).
2. **Given** a 2-Step Challenge backtest, **When** profit reaches 10% (Phase 1) and then 5% (Phase 2) without violations, **Then** status is "PASSED".
3. **Given** an Instant Funding backtest, **When** profit reaches 8% without hitting the 5% trailing drawdown, **Then** status is "PASSED" (Prout Triggered).
4. **Given** any standard challenge, **When** trading days < 3, **Then** status is "INCOMPLETE".

---

### User Story 3 - Account Scaling / Progression (Priority: P2)

Simulate long-term capital growth using CTI's scaling plans. CTI accounts can scale up to $200k/$400k upon meeting 10% profit targets over 4-month review periods. Crucially, we need to track performance at each tier.

**New Requirement**: If a funded account hits a drawdown limit at a higher tier, it doesn't just fail; it **resets** to the initial entry-level account size.

**Independent Test**: Run a multi-year simulation where the account scales up twice, then hits a drawdown. Verify the next trade starts with the base account size (Tier 1).

**Acceptance Scenarios**:

1. **Given** a funded account (post-challenge), **When** profit hits 10% over 4 months, **Then** account size increases to the next tier defined in `cti_challenge_scaling_plan.json`.
2. **Given** an Instant Funding account, **When** profit hits 10%, **Then** account scales according to `cti_instant_scaling_plan.json`.
3. **Given** an account at Tier 3 ($20k), **When** Max Drawdown limits are breached, **Then** the account is **reset** to Tier 1 ($10k) for the next phase, and a "Failure" is recorded for Tier 3.
4. **Given** a complete scaling backtest, **When** report is generated, **Then** it displays a breakdown of Successes/Failures per Tier (e.g., "Tier 1: 3 Pass, 0 Fail", "Tier 2: 1 Pass, 1 Fail").

---

## Edge Cases

- **Metric Calculation**: Division by zero for Sharpe/Sortino if volatility is 0. (Handle gracefully with 0 or N/A).
- **Short Backtests**: Calculating streaks/metrics on very few trades (< 5) might be statistically insignificant but must not crash.
- **Scaling Timing**: If a trade is open during a scaling event, does position size adjust immediately? (Assumption: No, applies to next trade).
- **Reset Loop**: Theoretically, an infinite loop of Scale -> Fail -> Reset -> Scale is possible. The backtest must strictly adhere to the data duration or a max-reset limit.

## Clarifications

### Session 2026-01-14

- Q: Scaling Review Timing? -> A: Periodic (Evaluation occurs at fixed 4-month intervals).
- Q: Drawdown Evaluation Basis? -> A: Closed Balance Only (No intraday high/low estimation).
- Q: Aggregate PnL across Resets? -> A: Independent Lives (Report each attempt/life separately; do not sum PnL across resets).

## Requirements

### Functional Requirements

**Advanced Metrics**:

- **FR-001**: System MUST calculate Arithmetic Mean of Trade Durations.
- **FR-002**: System MUST calculate Risk-to-Reward Ratio (Average Win / Average Loss).
- **FR-003**: System MUST calculate Sharpe Ratio (Annualized excess return / Std Dev). _Assumption: Risk-free rate = 0_.
- **FR-004**: System MUST calculate Sortino Ratio (Annualized excess return / Downside Deviation).
- **FR-005**: System MUST calculate Profit Factor (Gross Wins / Gross Losses).
- **FR-006**: System MUST calculate Max Consecutive Wins and Losses.

**CTI Rules & Progression**:

- **FR-007**: System MUST support a `ChallengeConfig` object defining: `max_daily_loss_pct`, `max_total_drawdown_pct`, `profit_target_pct`, `min_trading_days`.
- **FR-008**: System MUST track Drawdown based on **Closed Trade Balance** only (ignoring intraday floating PnL).
- **FR-009**: System MUST track "Daily Starting Balance" to calculate Daily Loss.
- **FR-010**: System MUST fail the backtest if parameters are breached.
- **FR-011**: **Scaling Logic**: System MUST evaluate scaling criteria only at fixed 4-month intervals (Periodic Review).
- **FR-012**: **Reset Logic**: If a scaled account fails (hits drawdown), the system MUST reset the account balance to the initial "Entry Level" size and log a failure event.
- **FR-013**: **Tier Metrics**: System MUST report the count of Successes (Promotions) and Failures (Demotions/Losses) for each account tier distinctively.
- **FR-014**: **Metric Segmentation**: Metrics MUST be calculated per "Life" (Attempt). A reset creates a new Life. The final report MUST show metrics for the _active_ Life, with a summary table of previous Lives.

### Key Entities

- **MetricsResult**: Expanded data class containing all new statistical fields.
- **ChallengeStatus**: Enum (PASSED, FAILED_DAILY, FAILED_MAX_DD, FAILED_TIME, INCOMPLETE).
- **ChallengeConfig**: Configuration for prop firm rules.
- **ScalingReport**: Data structure mapping `TierLevel -> {Successes: int, Failures: int}`.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Backtest reports include 100% of the requested metrics: Duration, RRR, Sharpe, Sortino, Streaks, Win Rate.
- **SC-002**: A strategy violating CTI 4% Daily Loss is correctly flagged as FAILED in 100% of test cases.
- **SC-003**: Metric calculation overhead does not increase total backtest time by more than 5%.
- **SC-004**: Users can define custom challenge parameters (e.g., 5% daily loss instead of 4%) via configuration.

## Assumptions

- CTI "Day Trading" rules are the baseline: 10% Max Drawdown, 4% Daily Loss.
- Scaling simulation assumes "Growth" style where you withdraw profit and get capital increase, OR you keep profit and get increase. We will implement "Balance Step Up" (New Balance = Old Balance + Increase) for straightforward simulation.
- Metrics are calculated on _closed_ trades.
