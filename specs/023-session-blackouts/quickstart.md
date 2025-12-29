# Quickstart: Session Blackouts

**Feature**: 023-session-blackouts  
**Date**: 2025-12-28

## Overview

Session blackouts allow you to avoid entering trades during:

- **News events**: NFP, Initial Jobless Claims
- **Session gaps**: NY close → Asian open

## Quick Usage

### Enable News Blackouts

```python
from src.risk import RiskConfig
from src.risk.blackout import BlackoutConfig, NewsBlackoutConfig

# Create config with news blackouts enabled
risk_config = RiskConfig(
    blackout=BlackoutConfig(
        news=NewsBlackoutConfig(
            enabled=True,
            pre_close_minutes=10,  # Block entries 10min before event
            post_pause_minutes=30,  # Resume 30min after event
        )
    )
)
```

### Enable Session Blackouts

```python
from src.risk.blackout import SessionBlackoutConfig

risk_config = RiskConfig(
    blackout=BlackoutConfig(
        sessions=SessionBlackoutConfig(
            enabled=True,
            pre_close_minutes=10,  # Block entries 10min before NY close
            post_pause_minutes=5,  # Resume 5min after Asian open
        )
    )
)
```

### Enable Both

```python
risk_config = RiskConfig(
    blackout=BlackoutConfig(
        news=NewsBlackoutConfig(enabled=True),
        sessions=SessionBlackoutConfig(enabled=True),
    )
)
```

## CLI Usage (Planned)

```bash
# Run backtest with news blackouts
python -m src.cli.run_backtest \
    --pair EURUSD \
    --blackout-news \
    --blackout-pre-close 10 \
    --blackout-post-pause 30

# Run backtest with session blackouts
python -m src.cli.run_backtest \
    --pair EURUSD \
    --blackout-sessions
```

## Generate News Calendar

```python
from src.risk.blackout.calendar import generate_news_calendar

# Generate calendar for 2023
events = generate_news_calendar(
    start_date=date(2023, 1, 1),
    end_date=date(2023, 12, 31),
    event_types=["NFP", "IJC"],
)

# Export to CSV
import pandas as pd
df = pd.DataFrame([e.__dict__ for e in events])
df.to_csv("news_calendar_2023.csv", index=False)
```

## Defaults

| Setting                       | Default | Description                         |
| ----------------------------- | ------- | ----------------------------------- |
| `news.enabled`                | `False` | Disabled by default                 |
| `news.pre_close_minutes`      | `10`    | Block entries 10min before          |
| `news.post_pause_minutes`     | `30`    | Resume 30min after                  |
| `news.force_close`            | `False` | Keep positions open                 |
| `sessions.enabled`            | `False` | Disabled by default                 |
| `sessions.pre_close_minutes`  | `10`    | Block entries 10min before NY close |
| `sessions.post_pause_minutes` | `5`     | Resume 5min after Asian open        |

## Verification

Check if blackouts are active:

```python
from src.risk.blackout.windows import is_in_blackout

# Check if a timestamp is in a blackout window
if is_in_blackout(bar_timestamp, blackout_windows):
    # Block new entry
    pass
```
