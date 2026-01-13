# Feature Specification: Fix Risk Argument Mapping

**Feature Branch**: `025-fix-risk-args`
**Created**: 2026-01-06
**Status**: Draft
**Input**: User description: "Bug: --rr-ratio and other risk CLI arguments are ignored in backtests"

## Clarifications

### Session 2026-01-06

- Q: Should `--max-position-size` be mapped even though it was excluded from the initial draft? -> A: Yes, map it (ensure complete coverage of reported issue).

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Risk Parameters Override (Priority: P1)

As a quantitative trader, I want my CLI risk arguments (Risk/Reward, ATR multiplier, Risk %) to control the backtest execution so that I can evaluate different risk management strategies without modifying code or config files.

**Why this priority**: Currently, these arguments are silently ignored, leading to incorrect backtest results that default to hardcoded values regardless of user input. This prevents accurate "what-if" analysis using the command line.

**Independent Test**: Can be fully tested by running backtests with different `--rr-ratio` values and observing different exit prices and PnL, confirming the strategy actually used the provided ratio.

**Acceptance Scenarios**:

1. **Given** a default strategy with a base Risk/Reward (R:R) of 2.0, **When** I run the backtest with an R:R argument of 5.0, **Then** the backtest results should reflect a 5.0 R:R ratio (e.g., larger wins, potentially lower win rate).
2. **Given** a strategy configuration, **When** I run with a Risk % argument of 1.0%, **Then** the position sizing should reflect 1% risk per trade instead of the default.
3. **Given** a strategy configuration, **When** I run with an ATR multiplier of 1.5, **Then** the stop loss distance should be tighter than the default 2.0 ATR.
4. **Given** a strategy configuration, **When** I run with a starting balance of 10000, **Then** the initial capital used for calculations should be 10,000.
5. **Given** a strategy configuration, **When** I run with a Max Position Size of 5.0, **Then** no trade size should exceed 5.0 lots.

---

### User Story 2 - Config File Precedence (Priority: P2)

As a user, I want CLI arguments to take precedence over configuration files so that I can temporarily override saved settings for quick experiments.

**Why this priority**: Ensures consistent and predictable behavior when mixing configuration methods.

**Independent Test**: Create a config file with one value, run CLI with a different value, and verify the CLI value is used.

**Acceptance Scenarios**:

1. **Given** a configuration file specifying an R:R of 2.0, **When** I run the backtest loading that config BUT specifically providing an R:R argument of 4.0, **Then** the utilized parameter should be 4.0.

### Requirements

- [x] **Risk Argument Mapping**: Map CLI arguments to `StrategyParameters` correctly.
- [x] **Precedence Logic**: Ensure CLI > Config > Defaults.
- [x] **Logging**: Log active risk parameters at startup.
- [x] **Max Position Size**: Add support for `max_position_size` parameter.
- [ ] **Trailing Stop Support**:
  - Support `ATR_Trailing` (existing but requires batch engine implementation).
  - Support `MA_Trailing` (stop follows a Moving Average).
  - Support `FixedPips_Trailing` (trail price by fixed pips).
  - Update CLI to accept trailing configuration (`--ma-type`, `--ma-period`).
  - Update `simulate_trades_batch` to handle dynamic trailing stops.

## Edge Cases

- **Conflicting Inputs**: If both a risk configuration file and individual risk arguments are provided, the individual arguments must take precedence.
- **Missing Defaults**: If no arguments are provided, the system must fall back to the safe defaults defined in the strategy configuration.
- **Invalid Inputs**: If negative values are provided for risk parameters (where invalid), the system should rely on existing validation logic to reject them (out of scope to add new validation, but mapping must preserve value for validation).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: The system MUST utilize the provided Reward-to-Risk ratio argument when calculating trade exit targets.
- **FR-002**: The system MUST utilize the provided ATR multiplier argument when calculating stop loss distances.
- **FR-003**: The system MUST utilize the provided Risk Percentage argument when determining position sizes.
- **FR-004**: The system MUST utilize the provided Starting Balance argument as the initial capital.
- **FR-005**: CLI arguments MUST override any conflicting values loaded from configuration files.
- **FR-006**: The system MUST log which risk parameters are being actively used to provide visibility to the user.
- **FR-007**: The system MUST utilize the provided Max Position Size argument to limit the maximum allowable trade size.

### Assumptions

- The underlying strategy engine supports dynamic configuration of these parameters.
- Existing validation logic defined in the configuration layer is sufficient to handle invalid values passed from CLI.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Running a backtest with an R:R of 3.0 produces different trade exits compared to an R:R of 2.0 (assuming winning trades exist).
- **SC-002**: The applied configuration verified in logs matches exactly the values provided via CLI arguments.
- **SC-003**: 100% of the documented risk arguments (Risk %, ATR multiplier, R:R, Starting Balance, Max Position Size) correctly alter the backtest behavior when specified.
