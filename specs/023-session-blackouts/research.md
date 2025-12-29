# Research: Session Blackouts + High-Impact News Avoidance

**Feature**: 023-session-blackouts  
**Date**: 2025-12-28

## Overview

This document captures research findings for implementing rule-based blackout windows for backtesting without external data dependencies.

---

## Decision 0: Vectorized Implementation (CRITICAL)

**Decision**: All blackout filtering MUST be vectorized using NumPy boolean masks

**Rationale**:

- Existing scan/simulation pipeline is fully vectorized for performance
- Per-candle loops would regress performance by orders of magnitude
- `filter_blackout_signals` must work on arrays, not iterate bar-by-bar

**Implementation Pattern**:

```python
def filter_blackout_signals(
    signal_indices: np.ndarray,
    timestamps: np.ndarray,  # UTC timestamps for each signal
    blackout_windows: list[tuple[datetime, datetime]],
) -> np.ndarray:
    """Vectorized blackout filter - O(n*w) where w = number of windows."""
    mask = np.ones(len(signal_indices), dtype=bool)
    for start, end in blackout_windows:
        # Vectorized comparison - no per-candle loop
        in_window = (timestamps >= start) & (timestamps <= end)
        mask &= ~in_window
    return signal_indices[mask]
```

**Prohibited Patterns**:

```python
# ❌ NEVER DO THIS - per-candle loop
for i, ts in enumerate(timestamps):
    if is_in_blackout(ts, windows):
        # ... per-bar logic
```

---

## Decision 1: Timezone Handling

**Decision**: Use `zoneinfo` (Python 3.9+ stdlib) for timezone conversions

**Rationale**:

- Part of Python standard library (no new dependencies)
- Handles DST transitions correctly
- Supports IANA timezone database

**Alternatives Considered**:

- `pytz`: Legacy library, being replaced by `zoneinfo`
- `dateutil`: Additional dependency, `zoneinfo` sufficient for our needs

---

## Decision 2: NFP Schedule Rule

**Decision**: First Friday of each month at 08:30 America/New_York

**Rationale**:

- Historically consistent schedule since 1939
- BLS releases at 08:30 ET
- "First Friday" rule is deterministic and well-documented

**Algorithm**:

```python
def first_friday_of_month(year: int, month: int) -> date:
    """Find first Friday of the given month."""
    first_day = date(year, month, 1)
    days_until_friday = (4 - first_day.weekday()) % 7  # Friday = 4
    return first_day + timedelta(days=days_until_friday)
```

**Edge Cases**:

- If first Friday is Jan 1 (holiday): BLS typically shifts to second Friday — handle via holiday skip

---

## Decision 3: IJC Schedule Rule

**Decision**: Every Thursday at 08:30 America/New_York

**Rationale**:

- Weekly release schedule on Thursday mornings
- Most consistent high-frequency economic indicator

**Algorithm**:

```python
def thursdays_in_range(start: date, end: date) -> list[date]:
    """Generate all Thursdays in date range."""
    # Start from first Thursday >= start
    days_until_thursday = (3 - start.weekday()) % 7  # Thursday = 3
    current = start + timedelta(days=days_until_thursday)
    thursdays = []
    while current <= end:
        thursdays.append(current)
        current += timedelta(days=7)
    return thursdays
```

---

## Decision 4: U.S. Market Holidays

**Decision**: Hard-coded list of major NYSE holidays

**Rationale**:

- Only ~10 holidays per year
- Schedule is well-defined and rarely changes
- No external library needed

**Holidays to Track**:

| Holiday          | Rule                        |
| ---------------- | --------------------------- |
| New Year's Day   | January 1 (observed)        |
| MLK Day          | 3rd Monday of January       |
| Presidents Day   | 3rd Monday of February      |
| Good Friday      | Friday before Easter Sunday |
| Memorial Day     | Last Monday of May          |
| Juneteenth       | June 19 (since 2021)        |
| Independence Day | July 4 (observed)           |
| Labor Day        | 1st Monday of September     |
| Thanksgiving     | 4th Thursday of November    |
| Christmas        | December 25 (observed)      |

**Observed Rules**:

- If holiday falls on Saturday → observed Friday
- If holiday falls on Sunday → observed Monday

---

## Decision 5: Session Anchors

**Decision**: Use fixed local times for NY close and Asian open

**Rationale**:

- NY close: 17:00 America/New_York (consistent)
- Asian open: 09:00 Asia/Tokyo (Tokyo Stock Exchange)
- Gap is approximately 12-16 hours depending on DST

**Configuration**:

```python
SESSION_ANCHORS = {
    "ny_close": ("17:00", "America/New_York"),
    "asian_open": ("09:00", "Asia/Tokyo"),
}
```

---

## Decision 6: Window Merge Algorithm

**Decision**: Interval union using sorted endpoints

**Rationale**:

- O(n log n) complexity for n windows
- Clean handling of overlaps and adjacent intervals
- Well-understood algorithm

**Algorithm**:

```python
def merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """Merge overlapping/adjacent intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        if start <= merged[-1][1]:  # Overlaps or adjacent
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged
```

---

## Decision 7: Telemetry Counters

**Decision**: Use Python `logging` with structured fields

**Rationale**:

- Consistent with existing codebase patterns
- No new dependencies
- Can be enhanced later with metrics library if needed

**Counters to Track**:

- `events_loaded`: Total calendar events generated
- `windows_built`: Total blackout windows created
- `windows_merged`: Windows combined due to overlap
- `entries_blocked`: Signals filtered due to blackout
- `force_closes`: Positions closed before blackout (when enabled)

---

## Open Items

None — all research questions resolved.
