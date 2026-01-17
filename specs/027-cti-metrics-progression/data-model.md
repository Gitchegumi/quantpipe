# Data Models

## Domain Models (`src/risk/prop_firm/models.py`)

### `ChallengeConfig`

Configuration for a specific Prop Firm challenge.

```python
@dataclass(frozen=True)
class ChallengeConfig:
    program_id: str                   # e.g., "CTI_1STEP_10K"
    account_size: float               # Starting balance
    max_daily_loss_pct: float         # e.g., 0.04
    max_total_drawdown_pct: float     # e.g., 0.05
    profit_target_pct: float          # e.g., 0.10
    min_trading_days: int             # e.g., 5
    max_time_days: int | None = None  # None = Unlimited
    drawdown_mode: str = "CLOSED_BALANCE"  # Future proofing
```

### `ScalingConfig`

Configuration for scaling rules.

```python
@dataclass(frozen=True)
class ScalingConfig:
    review_period_months: int         # e.g., 4
    profit_target_pct: float          # e.g., 0.10
    increments: List[float]           # Tier balances: [10000, 20000, 40000...]
    # Logic: If current balance == increments[i], next is increments[i+1]
```

### `LifeResult`

The result of a single "Life" (Attempt) within a scaling simulation.

```python
@dataclass(frozen=True)
class LifeResult:
    life_id: int                      # 1-based index
    start_tier_balance: float
    end_balance: float
    status: str                       # PASSED, FAILED_DRAWDOWN, FAILED_DAILY, IN_PROGRESS
    start_date: datetime
    end_date: datetime
    trade_count: int
    pnl: float
    metrics: MetricsSummary           # Independent metrics for this life
```

### `ScalingReport`

The aggregate report of a multi-life simulation.

```python
@dataclass(frozen=True)
class ScalingReport:
    lives: List[LifeResult]
    total_duration_days: int
    active_life_index: int            # Index of the current active life in `lives`

    @property
    def tier_stats(self) -> Dict[float, Dict[str, int]]:
        # Returns {10000: {'success': 2, 'fail': 1}, ...}
        pass
```

## Core Model Updates (`src/models/core.py`)

### `MetricsSummary`

Update with new fields (all optional/defaulting to NaN for backward compat logic if instantiated manually, though dataclass prevents that easily - will need careful migration or default values).

```python
@dataclass(frozen=True)
class MetricsSummary:
    # ... existing fields ...
    sortino_ratio: float = float('nan')
    avg_trade_duration_seconds: float = float('nan')
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    annualized_volatility: float = float('nan')
```
