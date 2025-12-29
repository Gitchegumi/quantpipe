# Data Model: Session Blackouts

**Feature**: 023-session-blackouts  
**Date**: 2025-12-28

## Entities

### NewsEvent

Represents a scheduled economic news release.

| Field            | Type                        | Description                           | Validation            |
| ---------------- | --------------------------- | ------------------------------------- | --------------------- |
| `event_name`     | `str`                       | Event identifier (e.g., "NFP", "IJC") | Required, non-empty   |
| `currency`       | `str`                       | Currency affected (e.g., "USD")       | Required, 3-char code |
| `event_time_utc` | `datetime`                  | Scheduled release time in UTC         | Required, tz-aware    |
| `impact_level`   | `Literal["high", "medium"]` | Event impact level                    | Default: "high"       |

**Relationships**: None (standalone entity)

**State Transitions**: N/A (immutable after creation)

---

### BlackoutWindow

Represents a time period during which new trade entries are blocked.

| Field       | Type                         | Description              | Validation                  |
| ----------- | ---------------------------- | ------------------------ | --------------------------- |
| `start_utc` | `datetime`                   | Window start time in UTC | Required, tz-aware          |
| `end_utc`   | `datetime`                   | Window end time in UTC   | Required, tz-aware, > start |
| `source`    | `Literal["news", "session"]` | Origin of the window     | Required                    |

**Relationships**: May be derived from `NewsEvent`

**State Transitions**: N/A (immutable after creation)

**Invariants**:

- `end_utc > start_utc`
- Both timestamps must be timezone-aware

---

### NewsBlackoutConfig

Configuration for news-based blackout windows.

| Field                | Type        | Description                                  | Default          |
| -------------------- | ----------- | -------------------------------------------- | ---------------- |
| `enabled`            | `bool`      | Enable news blackouts                        | `False`          |
| `pre_close_minutes`  | `int`       | Minutes before event to start blackout       | `10`             |
| `post_pause_minutes` | `int`       | Minutes after event to end blackout          | `30`             |
| `force_close`        | `bool`      | Force-close open positions at blackout start | `False`          |
| `event_types`        | `list[str]` | Event types to include                       | `["NFP", "IJC"]` |

**Validation**:

- `pre_close_minutes >= 0`
- `post_pause_minutes >= 0`
- `event_types` must not be empty when `enabled=True`

---

### SessionBlackoutConfig

Configuration for session-based blackout windows.

| Field                | Type   | Description                      | Default              |
| -------------------- | ------ | -------------------------------- | -------------------- |
| `enabled`            | `bool` | Enable session blackouts         | `False`              |
| `pre_close_minutes`  | `int`  | Minutes before NY close to start | `10`                 |
| `post_pause_minutes` | `int`  | Minutes after Asian open to end  | `5`                  |
| `force_close`        | `bool` | Force-close open positions       | `False`              |
| `ny_close_time`      | `str`  | NY close time (HH:MM format)     | `"17:00"`            |
| `asian_open_time`    | `str`  | Asian open time (HH:MM format)   | `"09:00"`            |
| `ny_timezone`        | `str`  | Timezone for NY close            | `"America/New_York"` |
| `asian_timezone`     | `str`  | Timezone for Asian open          | `"Asia/Tokyo"`       |

**Validation**:

- Time strings must be valid HH:MM format
- Timezone strings must be valid IANA identifiers

---

### BlackoutConfig

Top-level configuration combining news and session blackouts.

| Field      | Type                    | Description               | Default             |
| ---------- | ----------------------- | ------------------------- | ------------------- |
| `news`     | `NewsBlackoutConfig`    | News blackout settings    | Disabled by default |
| `sessions` | `SessionBlackoutConfig` | Session blackout settings | Disabled by default |

**Integration**: Added as optional field to existing `RiskConfig`:

```python
class RiskConfig(BaseModel):
    # ... existing fields ...
    blackout: BlackoutConfig | None = None
```

---

## Generated Calendar Schema

When exported to CSV/Parquet:

| Column               | Type       | Description                      |
| -------------------- | ---------- | -------------------------------- |
| `event`              | `string`   | Event name (NFP, IJC)            |
| `currency`           | `string`   | Currency code (USD)              |
| `impact`             | `string`   | Impact level (high, medium)      |
| `event_time_utc`     | `datetime` | Scheduled event time             |
| `blackout_start_utc` | `datetime` | Window start (event - pre_close) |
| `blackout_end_utc`   | `datetime` | Window end (event + post_pause)  |
