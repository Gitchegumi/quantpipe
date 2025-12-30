# Feature Specification: Session Blackouts + High-Impact News Avoidance

**Feature Branch**: `023-session-blackouts`  
**Created**: 2025-12-28  
**Status**: Draft  
**Input**: GitHub Issue #19 - Optional backtesting flags for session blackouts and news avoidance integrated into `src.risk`

## Clarifications

### Session 2025-12-28

- Q: What should the default force-close behavior be when entering a blackout window? → A: Default OFF - Positions remain open during blackouts; only new entries blocked.
- Q: Should currency-based filtering be included in the initial implementation scope? → A: Global mode only (defer `by_currency`); all instruments blocked during any news event.
- Q: How should the calendar generator handle U.S. market holidays? → A: Skip holidays - Do not generate events on known U.S. market holidays.

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Enable News Blackouts During Backtests (Priority: P1)

A trader running backtests wants to avoid entering new positions during high-impact economic news releases (e.g., NFP, Initial Jobless Claims) to improve strategy robustness and reduce exposure to unpredictable volatility.

**Why this priority**: News events cause the most significant backtesting distortion. Avoiding these windows removes regime-breaking behavior without requiring external data dependencies.

**Independent Test**: Can be tested by running a backtest with `news.enabled=True` and verifying that no new entries occur within defined news blackout windows.

**Acceptance Scenarios**:

1. **Given** a backtest configuration with `news.enabled=True`, **When** the simulation reaches a bar within 10 minutes before an NFP release, **Then** the system blocks new trade entries until 30 minutes after the event.
2. **Given** a backtest with `news.enabled=True` and an open position, **When** the simulation reaches 10 minutes before the news event, **Then** optionally the position may be force-closed (configurable behavior).
3. **Given** a backtest with `news.enabled=False` (default), **When** the simulation runs through news event times, **Then** trade entries proceed normally with no filtering.

---

### User Story 2 - Enable Session Blackouts During Backtests (Priority: P2)

A trader wants to avoid entering positions during low-liquidity periods (e.g., between New York close and Asian open) to reduce slippage risk and improve backtest realism.

**Why this priority**: Session-based blackouts improve backtest quality by avoiding known illiquid periods, but are less impactful than news events.

**Independent Test**: Can be tested by running a backtest with `sessions.enabled=True` and verifying no new entries occur during the NY close → Asian open window.

**Acceptance Scenarios**:

1. **Given** a backtest with `sessions.enabled=True`, **When** the bar timestamp falls within 10 minutes before NY close through 5 minutes after Asian open, **Then** new entries are blocked.
2. **Given** a backtest with `sessions.enabled=True` and an open position, **When** the simulation reaches 10 minutes before NY close, **Then** optionally the position may be force-closed (configurable).
3. **Given** a backtest with `sessions.enabled=False` (default), **When** the simulation runs through session transition times, **Then** trade entries proceed normally.

---

### User Story 3 - Generate Rule-Based News Calendar (Priority: P3)

A trader wants to generate a deterministic, rule-based economic calendar for known recurring events (NFP, IJC) without external data dependencies, enabling reproducible backtests across any historical period (2001–present).

**Why this priority**: Enables fully offline, reproducible backtesting without API calls or licensing concerns.

**Independent Test**: Can be tested by generating a calendar for a date range and verifying events match expected schedules (e.g., NFP on first Friday of each month at 08:30 ET).

**Acceptance Scenarios**:

1. **Given** a request to generate events for 2020-01-01 to 2020-12-31, **When** the calendar generator runs, **Then** it produces 52 IJC events (every Thursday) and 12 NFP events (first Friday of each month).
2. **Given** a generated event, **When** inspected, **Then** the event includes `event_time_utc`, `blackout_start_utc`, and `blackout_end_utc` with correct timezone conversion.

---

### Edge Cases

- What happens when a news event and session blackout overlap? Windows should be merged into a single continuous blackout period.
- What happens at DST transitions? All times must use timezone-aware timestamps and convert correctly to UTC.
- What happens with multi-timeframe data (1m vs 1D bars)? Blackout windows apply based on bar close timestamps in UTC.
- What happens if no calendar is provided but `news.enabled=True`? System should generate a default rule-based calendar.
- What happens when a scheduled event falls on a U.S. market holiday? Skip the event (no blackout generated for non-existent releases).

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: System MUST support optional `news.enabled` and `sessions.enabled` flags in backtester configuration (default: `False`).
- **FR-002**: When `news.enabled=True`, system MUST block new trade entries from `event_time - pre_close_minutes` through `event_time + post_pause_minutes`.
- **FR-003**: When `sessions.enabled=True`, system MUST block new trade entries from `ny_close - pre_close_minutes` through `asian_open + post_pause_minutes`.
- **FR-004**: System MUST provide configurable `pre_close_minutes` (default: 10) and `post_pause_minutes` (default: 30 for news, 5 for sessions).
- **FR-005**: System MUST support optional force-close behavior for open positions when entering a blackout window. Default: OFF (positions remain open; only new entries blocked).
- **FR-006**: System MUST generate rule-based calendars for known recurring events (NFP, IJC) without external data.
- **FR-007**: System MUST handle timezone conversions correctly, including DST transitions.
- **FR-008**: System MUST merge overlapping blackout windows into single continuous periods.
- **FR-009**: Initial implementation uses global mode only (all instruments blocked during news events). Currency-based filtering (`by_currency` mode) is deferred to a future enhancement.
- **FR-010**: System MUST emit telemetry for events loaded, windows built, entries blocked, and positions force-closed.
- **FR-011**: Blackout logic MUST integrate into `src.risk` module as optional policies.

### Key Entities

- **BlackoutWindow**: Represents a period during which trade entries are blocked. Contains `start_utc`, `end_utc`, optional `currencies` set, and source (`news` | `session`).
- **NewsEvent**: Represents a scheduled economic release with `event_name`, `currency`, `impact_level`, `event_time_utc`.
- **SessionAnchors**: Configuration for session boundaries (NY close time, Asian open time, applicable timezones).
- **BlackoutConfig**: Configuration for blackout behavior including `news.enabled`, `sessions.enabled`, timing offsets, and force-close settings.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Backtests with blackouts enabled show zero new entries during configured blackout windows.
- **SC-002**: Rule-based calendar generation produces identical results for the same date range across multiple runs (deterministic).
- **SC-003**: Telemetry accurately counts blocked entries and force-closed positions matching actual simulation behavior.
- **SC-004**: All timestamp operations remain correct across DST boundaries (verified via unit tests).
- **SC-005**: Blackout configuration requires no external API calls or network access.
