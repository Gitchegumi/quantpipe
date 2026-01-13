# Data Model: Fix Risk Argument Mapping

## StrategyParameters Update

**Location**: `src/config/parameters.py`

### New Fields

| Field               | Type    | Default | Description                   | Constraints          |
| ------------------- | ------- | ------- | ----------------------------- | -------------------- |
| `max_position_size` | `float` | `10.0`  | Maximum position size in lots | `gt=0.0`, `le=100.0` |

### Existing Fields (for context)

- `target_r_mult`: float (Mapped from `--rr-ratio`)
- `atr_stop_mult`: float (Mapped from `--atr-mult`)
- `risk_per_trade_pct`: float (Mapped from `--risk-pct`)
- `account_balance`: float (Mapped from `--starting-balance`)
