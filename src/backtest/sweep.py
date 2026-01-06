"""Parameter sweep orchestration for indicator testing.

This module provides the core data structures and functions for running
parallel parameter sweeps across indicator configurations.
"""

import csv
import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from ..config.parameters import StrategyParameters
from ..models.enums import DirectionMode
from .engine import construct_data_paths, run_portfolio_backtest
from .parallel import get_worker_count


logger = logging.getLogger(__name__)


@dataclass
class ParameterRange:
    """Represents user input for a single indicator parameter.

    Attributes:
        indicator_name: Semantic indicator name (e.g., "fast_ema").
        param_name: Parameter key (e.g., "period").
        values: Expanded list of values to test.
        is_range: True if user specified a range, False for single value.
        default: The default value from the indicator registry.
    """

    indicator_name: str
    param_name: str
    values: list[int | float]
    is_range: bool = False
    default: int | float = 0


@dataclass
class ParameterSet:
    """A specific combination of all parameter values for one backtest.

    Attributes:
        params: Nested dict {indicator_name: {param_name: value}}.
        label: Human-readable label for results display.
    """

    params: dict[str, dict[str, Any]]
    label: str = ""

    def __post_init__(self) -> None:
        """Generate label from params if not provided."""
        if not self.label:
            parts = []
            for ind_name, ind_params in sorted(self.params.items()):
                for param_name, val in sorted(ind_params.items()):
                    parts.append(f"{ind_name}.{param_name}={val}")
            self.label = ", ".join(parts)


@dataclass
class SweepConfig:
    """Configuration collected from user prompts for a parameter sweep.

    Attributes:
        strategy_name: Name of the strategy being tested.
        ranges: All parameter ranges collected from user.
        total_combinations: Total size of cartesian product.
        valid_combinations: Combinations remaining after constraint filtering.
        skipped_count: Number of combinations filtered by constraints.
    """

    strategy_name: str
    ranges: list[ParameterRange] = field(default_factory=list)
    total_combinations: int = 0
    valid_combinations: int = 0
    skipped_count: int = 0


# Range parsing patterns
RANGE_PATTERN = re.compile(
    r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s+step\s+(\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)
SINGLE_VALUE_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)$")


def parse_range_input(
    input_str: str, default: int | float, param_type: type = int
) -> tuple[list[int | float], bool]:
    """Parse user input into a list of parameter values.

    Args:
        input_str: Raw user input string.
        default: Default value to use if input is empty.
        param_type: Type to cast values to (int or float).

    Returns:
        Tuple of (values list, is_range flag).

    Raises:
        ValueError: If input format is invalid.

    Examples:
        >>> parse_range_input("", 20, int)
        ([20], False)
        >>> parse_range_input("15", 20, int)
        ([15], False)
        >>> parse_range_input("10-30 step 5", 20, int)
        ([10, 15, 20, 25, 30], True)
    """
    input_str = input_str.strip()

    # Empty input uses default
    if not input_str:
        return [param_type(default)], False

    # Try single value
    single_match = SINGLE_VALUE_PATTERN.match(input_str)
    if single_match:
        value = param_type(float(single_match.group(1)))
        return [value], False

    # Try range syntax
    range_match = RANGE_PATTERN.match(input_str)
    if range_match:
        start = float(range_match.group(1))
        end = float(range_match.group(2))
        step = float(range_match.group(3))

        if step <= 0:
            msg = "Step must be positive"
            raise ValueError(msg)
        if start > end:
            msg = "Start must be <= end"
            raise ValueError(msg)

        values = []
        current = start
        while current <= end + (step / 100):  # Small epsilon for float comparison
            values.append(param_type(current))
            current += step

        if not values:
            msg = "Range produced no values"
            raise ValueError(msg)

        return values, True

    msg = (
        f"Invalid input format: '{input_str}'. "
        "Use a single value (e.g., '15') or range syntax (e.g., '10-30 step 5')."
    )
    raise ValueError(msg)


def generate_combinations(
    ranges: list[ParameterRange],
) -> list[ParameterSet]:
    """Generate cartesian product of all parameter ranges.

    Args:
        ranges: List of ParameterRange objects.

    Returns:
        List of ParameterSet objects, one per combination.
    """
    if not ranges:
        return []

    # Group ranges by indicator
    ranges_by_indicator: dict[str, list[ParameterRange]] = {}
    for r in ranges:
        if r.indicator_name not in ranges_by_indicator:
            ranges_by_indicator[r.indicator_name] = []
        ranges_by_indicator[r.indicator_name].append(r)

    # Build value lists for cartesian product
    param_keys: list[tuple[str, str]] = []
    value_lists: list[list[int | float]] = []

    for ind_name in sorted(ranges_by_indicator.keys()):
        for r in ranges_by_indicator[ind_name]:
            param_keys.append((ind_name, r.param_name))
            value_lists.append(r.values)

    # Generate cartesian product
    combinations = []
    for combo in product(*value_lists):
        params: dict[str, dict[str, Any]] = {}
        for (ind_name, param_name), value in zip(param_keys, combo, strict=False):
            if ind_name not in params:
                params[ind_name] = {}
            params[ind_name][param_name] = value
        combinations.append(ParameterSet(params=params))

    return combinations


def filter_invalid_combinations(
    combinations: list[ParameterSet],
    constraints: list[Callable[[ParameterSet], bool]] | None = None,
) -> tuple[list[ParameterSet], int]:
    """Filter out invalid parameter combinations.

    Default constraint: fast_ema.period < slow_ema.period

    Args:
        combinations: List of ParameterSet objects.
        constraints: Optional list of constraint functions.
            Each function returns True if combination is VALID.

    Returns:
        Tuple of (valid combinations, count of skipped).
    """
    if constraints is None:
        # Default constraint: fast EMA period must be less than slow EMA period
        def ema_constraint(ps: ParameterSet) -> bool:
            fast = ps.params.get("fast_ema", {}).get("period")
            slow = ps.params.get("slow_ema", {}).get("period")
            if fast is None or slow is None:
                return True  # No EMA constraint if not present
            return fast < slow

        constraints = [ema_constraint]

    valid = []
    skipped = 0

    for combo in combinations:
        if all(constraint(combo) for constraint in constraints):
            valid.append(combo)
        else:
            skipped += 1

    if skipped > 0:
        logger.info("Filtered %d invalid combinations", skipped)

    return valid, skipped


@dataclass
class SingleResult:
    """Result from one backtest with a specific parameter set.

    Attributes:
        params: Parameters used for this backtest.
        sharpe_ratio: Sharpe ratio of returns.
        total_pnl: Total profit/loss in currency.
        win_rate: Percentage of winning trades.
        trade_count: Number of trades executed.
        max_drawdown: Maximum drawdown percentage.
        error: Error message if backtest failed, None otherwise.
    """

    params: ParameterSet
    sharpe_ratio: float = 0.0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    trade_count: int = 0
    max_drawdown: float = 0.0
    error: str | None = None


@dataclass
class SweepResult:
    """Aggregated results from all parameter combinations.

    Attributes:
        results: List of per-combination results.
        best_params: Highest-ranked parameter set.
        ranking_metric: Metric used for ranking (e.g., "sharpe_ratio").
        execution_time_seconds: Total sweep duration.
        total_combinations: Number of combinations tested.
        successful_count: Number that completed without error.
        failed_count: Number that failed with error.
    """

    results: list[SingleResult] = field(default_factory=list)
    best_params: ParameterSet | None = None
    ranking_metric: str = "sharpe_ratio"
    execution_time_seconds: float = 0.0
    total_combinations: int = 0
    successful_count: int = 0
    failed_count: int = 0


def rank_results(
    results: list[SingleResult],
    metric: str = "sharpe_ratio",
    ascending: bool = False,
) -> list[SingleResult]:
    """Rank results by specified metric.

    Args:
        results: List of SingleResult objects.
        metric: Metric to sort by (sharpe_ratio, total_pnl, win_rate).
        ascending: If True, sort ascending; otherwise descending.

    Returns:
        Sorted list of SingleResult objects.
    """
    # Filter out failed results
    successful = [r for r in results if r.error is None]

    # Sort by metric
    return sorted(
        successful,
        key=lambda r: getattr(r, metric, 0.0),
        reverse=not ascending,
    )


def display_results_table(
    results: list[SingleResult],
    top_n: int = 10,
) -> None:
    """Display results table using Rich.

    Args:
        results: Ranked list of SingleResult objects.
        top_n: Number of top results to display.
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    table = Table(title=f"Top {min(top_n, len(results))} Results by Sharpe Ratio")
    table.add_column("Rank", style="dim", width=4)
    table.add_column("fast_ema", style="cyan")
    table.add_column("slow_ema", style="cyan")
    table.add_column("Sharpe", style="green")
    table.add_column("Win Rate", style="yellow")
    table.add_column("PnL", style="magenta")
    table.add_column("Trades", style="dim")

    for i, result in enumerate(results[:top_n], 1):
        fast_period = result.params.params.get("fast_ema", {}).get("period", "-")
        slow_period = result.params.params.get("slow_ema", {}).get("period", "-")

        table.add_row(
            str(i),
            str(fast_period),
            str(slow_period),
            f"{result.sharpe_ratio:.2f}",
            f"{result.win_rate:.1%}",
            f"${result.total_pnl:.2f}",
            str(result.trade_count),
        )

    console.print()
    console.print(table)


def run_single_backtest(
    params: ParameterSet,
    pair_paths: list[tuple[str, Path]],
    direction_mode: DirectionMode = DirectionMode.LONG,
    starting_equity: float = 2500.0,
    dataset: str = "test",
) -> SingleResult:
    """Run a single backtest with specific parameters.

    Args:
        params: Parameters to test.
        pair_paths: Pre-constructed lists of (pair, path) tuples.
        direction_mode: Trading direction (LONG/SHORT/BOTH).
        starting_equity: Starting capital.
        dataset: Dataset name (for logging).

    Returns:
        SingleResult object with performance metrics.
    """
    try:
        # Create base strategy params (with defaults)
        strategy_params = StrategyParameters()

        # Inject parameter sweep values into strategy parameters
        # Note: StrategyParameters works with 'ema_fast', 'ema_slow', 'atr_length', 'rsi_length'
        # ParameterSet uses 'fast_ema', 'slow_ema', 'atr', 'rsi'

        # Mapping: indicator_name -> strategy_param_field
        # (Only mapping fields that exist in StrategyParameters for consistency)
        # Note: We also pass all params as override dict to engine, so semantic names are preserved.

        fast_ema_period = params.params.get("fast_ema", {}).get("period")
        if fast_ema_period:
            strategy_params.ema_fast = int(fast_ema_period)

        slow_ema_period = params.params.get("slow_ema", {}).get("period")
        if slow_ema_period:
            strategy_params.ema_slow = int(slow_ema_period)

        atr_period = params.params.get("atr", {}).get("period")
        if atr_period:
            strategy_params.atr_length = int(atr_period)

        rsi_period = params.params.get("rsi", {}).get("period")
        if rsi_period:
            strategy_params.rsi_length = int(rsi_period)

        # Run backtest using the engine
        # We pass params.params as indicator_overrides to support arbitrary indicator sweeping
        result, _ = run_portfolio_backtest(
            pair_paths=pair_paths,
            direction_mode=direction_mode,
            strategy_params=strategy_params,
            starting_equity=starting_equity,
            dry_run=False,
            show_progress=False,  # Suppress inner progress bars
            indicator_overrides=params.params,
        )

        # Extract metrics
        # Extract metrics
        # Note: PortfolioResult has flat attributes, not a metrics object
        trade_count = getattr(result, "total_trades", 0)
        total_pnl = getattr(result, "total_pnl", 0.0)

        # Calculate derived metrics
        closed_trades = getattr(result, "closed_trades", [])
        wins = sum(1 for t in closed_trades if t.pnl_dollars > 0)
        win_rate = wins / trade_count if trade_count > 0 else 0.0

        # Calculate Max Drawdown from equity curve
        max_drawdown = 0.0
        equity_curve = getattr(result, "equity_curve", [])
        if equity_curve:
            peak = equity_curve[0][1]
            for _, equity in equity_curve:
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak
                if dd > max_drawdown:
                    max_drawdown = dd

        # Calculate Sharpe (Simple trade-based approximation)
        sharpe_ratio = 0.0
        if trade_count > 1:
            # Use pnl_r for return distribution
            returns = [t.pnl_r for t in closed_trades]
            if len(returns) > 1:
                import statistics

                try:
                    avg_ret = statistics.mean(returns)
                    std_dev = statistics.stdev(returns)
                    if std_dev > 0:
                        sharpe_ratio = avg_ret / std_dev
                except statistics.StatisticsError:
                    pass

        return SingleResult(
            params=params,
            sharpe_ratio=sharpe_ratio,
            total_pnl=total_pnl,
            win_rate=win_rate,
            trade_count=trade_count,
            max_drawdown=max_drawdown,
        )

    except Exception as e:
        logger.exception("Backtest failed for params %s", params.label)
        return SingleResult(params=params, error=str(e))


@dataclass
class SweepTask:
    """Container for a single backtest task execution args."""

    params: ParameterSet
    pair_paths: list[tuple[str, Path]]
    direction_mode: DirectionMode
    dataset: str
    starting_equity: float


def execute_sweep_task(task: SweepTask) -> SingleResult:
    """Worker function to execute a single backtest task."""
    return run_single_backtest(
        params=task.params,
        pair_paths=task.pair_paths,
        direction_mode=task.direction_mode,
        starting_equity=task.starting_equity,
        dataset=task.dataset,
    )


def run_sweep(
    combinations: list[ParameterSet],
    pairs: list[str],
    dataset: str = "test",
    direction: str = "LONG",
    max_workers: int | None = None,
    sequential: bool = False,
) -> SweepResult:
    """Run parameter sweep backtests sequentially (Phase 4 MVP).

    Args:
        combinations: List of parameter sets to test.
        pairs: List of currency pairs.
        dataset: Dataset partition.
        direction: Trading direction.

    Returns:
        SweepResult containing all results and metadata.
    """
    logger.info("Starting sweep with %d combinations", len(combinations))

    start_time = time.time()
    results = []

    # Construct data paths once (though engine currently reloads data, unfortunately)
    # TODO: Optimize engine to accept preloaded data
    pair_paths = construct_data_paths(pairs, dataset)
    direction_mode = DirectionMode[direction]

    successful = 0
    failed = 0

    # Determine execution mode
    worker_count = 1
    if not sequential:
        worker_count = get_worker_count(max_workers)

    logger.info("Running sweep with %d workers (concurrent)", worker_count)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task_id = progress.add_task("Running sweep...", total=len(combinations))

        if worker_count > 1:
            # Parallel Execution
            tasks = [
                SweepTask(
                    params=params,
                    pair_paths=pair_paths,
                    direction_mode=direction_mode,
                    dataset=dataset,
                    starting_equity=2500.0,  # pass default for now
                )
                for params in combinations
            ]

            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                futures = {
                    executor.submit(execute_sweep_task, task): i
                    for i, task in enumerate(tasks)
                }

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        if result.error:
                            failed += 1
                        else:
                            successful += 1
                    except Exception as e:
                        # This should be caught inside execute_sweep_task, but just in case
                        logger.error("Parallel task failed: %s", e)
                        failed += 1

                    progress.advance(task_id)
                    description = f"Tested {len(results)}/{len(combinations)}"
                    progress.update(task_id, description=description)

        else:
            # Sequential Execution
            for i, params in enumerate(combinations):
                progress.update(
                    task_id,
                    description=f"Testing {params.label} ({i+1}/{len(combinations)})",
                )

                result = run_single_backtest(
                    params=params,
                    pair_paths=pair_paths,
                    direction_mode=direction_mode,
                    dataset=dataset,
                )

                results.append(result)
                if result.error:
                    failed += 1
                else:
                    successful += 1

                progress.advance(task_id)

    execution_time = time.time() - start_time

    # Rank results
    ranked = rank_results(results)
    best = ranked[0].params if ranked else None

    return SweepResult(
        results=results,
        best_params=best,
        execution_time_seconds=execution_time,
        total_combinations=len(combinations),
        successful_count=successful,
        failed_count=failed,
    )


def export_results_to_csv(result: SweepResult, output_path: Path) -> None:
    """Export sweep results to CSV file.

    Args:
        result: The SweepResult object containing all execution data.
        output_path: Destination path for the CSV file.
    """
    if not result.results:
        logger.warning("No results to export.")
        return

    # Determine all unique parameter keys from the first result (assuming consistency)
    # Flatten structure: {ind: {param: val}} -> "ind_param"
    param_keys = []
    first_params = result.results[0].params.params
    for ind_name, ind_params in first_params.items():
        for p_name in ind_params:
            param_keys.append(f"{ind_name}_{p_name}")

    # Define CSV headers
    headers = [
        "rank",
        "sharpe_ratio",
        "total_pnl",
        "win_rate",
        "trade_count",
        "max_drawdown",
        "error",
    ] + param_keys

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            # Sort by Sharpe Descending
            sorted_results = sorted(
                result.results,
                key=lambda x: (x.sharpe_ratio if x.sharpe_ratio is not None else -999),
                reverse=True,
            )

            for i, r in enumerate(sorted_results):
                row = {
                    "rank": i + 1,
                    "sharpe_ratio": (
                        f"{r.sharpe_ratio:.4f}" if r.sharpe_ratio is not None else ""
                    ),
                    "total_pnl": f"{r.total_pnl:.2f}",
                    "win_rate": f"{r.win_rate:.4f}",
                    "trade_count": r.trade_count,
                    "max_drawdown": f"{r.max_drawdown:.4f}",
                    "error": r.error or "",
                }

                # Flatten params
                for ind_name, ind_params in r.params.params.items():
                    for p_name, p_val in ind_params.items():
                        row[f"{ind_name}_{p_name}"] = p_val

                writer.writerow(row)

        logger.info("Sweep results exported to %s", output_path)

    except OSError as e:
        logger.error("Failed to write export file %s: %s", output_path, e)
