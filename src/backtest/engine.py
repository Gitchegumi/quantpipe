"""
Core backtest execution engine.

This module encapsulates the high-level orchestration logic for running
backtests (single, multi-symbol, portfolio), separating it from the CLI
interface to allow programmatic usage (e.g., parameter sweeps).
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl

# Adjust relative imports for being in src/backtest/
from ..config.parameters import StrategyParameters
from ..data_io.ingestion import ingest_ohlcv_data
from ..indicators.dispatcher import calculate_indicators
from ..models.core import TradeExecution
from ..models.directional import BacktestResult
from ..models.enums import DirectionMode
from ..strategy.trend_pullback.signal_generator_vectorized import (
    generate_signals_vectorized,
)
from ..strategy.trend_pullback.strategy import TREND_PULLBACK_STRATEGY

from .orchestrator import BacktestOrchestrator
from .portfolio.portfolio_simulator import PortfolioSimulator

logger = logging.getLogger(__name__)

# Default account balance for multi-symbol concurrent PnL calculation (FR-003)
DEFAULT_ACCOUNT_BALANCE: float = 2500.0


def construct_data_paths(
    pairs: list[str],
    dataset: str,
    base_dir: Path = Path("price_data/processed"),
) -> list[tuple[str, Path]]:
    """Construct data paths for all specified pairs with validation.

    Iterates over all pairs, constructs paths for each (Parquet preferred,
    CSV fallback), and validates that at least one path exists.

    Args:
        pairs: List of currency pair codes (e.g., ['EURUSD', 'USDJPY'])
        dataset: Dataset partition to use ('test' or 'validate')
        base_dir: Base directory for processed data

    Returns:
        List of (pair, path) tuples for all valid pairs

    Raises:
        SystemExit: If no valid data paths found for any pair
    """
    pair_paths: list[tuple[str, Path]] = []
    missing_pairs: list[str] = []

    for pair in pairs:
        pair_lower = pair.lower()
        base_path = base_dir / pair_lower / dataset
        filename_base = f"{pair_lower}_{dataset}"

        # Try Parquet first (faster loading)
        parquet_path = base_path / f"{filename_base}.parquet"
        csv_path = base_path / f"{filename_base}.csv"

        if parquet_path.exists():
            pair_paths.append((pair, parquet_path))
            logger.info(
                "Constructed path for %s: %s",
                pair,
                parquet_path,
            )
        elif csv_path.exists():
            pair_paths.append((pair, csv_path))
            logger.info(
                "Constructed path for %s: %s (Parquet not found, using CSV)",
                pair,
                csv_path,
            )
        else:
            missing_pairs.append(pair)
            logger.warning(
                "No data file found for %s. Searched: %s, %s",
                pair,
                parquet_path,
                csv_path,
            )

    # Fail-fast validation (FR-006): All pairs must have data
    if missing_pairs and not pair_paths:
        print(
            f"Error: No data files found for any specified pairs: {missing_pairs}\n"
            f"Expected structure: price_data/processed/<pair>/<dataset>/"
            f"<pair>_<dataset>.[parquet|csv]\n"
            f"Use --data to specify a custom path for single-pair runs.",
            file=sys.stderr,
        )
        sys.exit(1)

    if missing_pairs:
        logger.warning(
            "Some pairs have no data files and will be skipped: %s",
            ", ".join(missing_pairs),
        )

    return pair_paths


def run_portfolio_backtest(
    pair_paths: list[tuple[str, Path]],
    direction_mode: DirectionMode,
    strategy_params,
    starting_equity: float = 2500.0,
    dry_run: bool = False,
    show_progress: bool = True,
    timeframe: str = "1m",
    blackout_config: Any = None,
    risk_config: Any = None,
    indicator_overrides: dict[str, dict[str, Any]] | None = None,
):
    """Run time-synchronized portfolio backtest with shared equity.

    All symbols trade against a shared running balance. Trades execute
    chronologically, with wins/losses affecting capital available for
    subsequent trades.

    Args:
        pair_paths: List of (pair, path) tuples from construct_data_paths()
        direction_mode: Direction mode (LONG/SHORT/BOTH)
        strategy_params: Strategy parameters to use
        starting_equity: Starting portfolio capital ($2,500 default)
        dry_run: If True, generate signals only without execution
        show_progress: If True, show progress bars
        indicator_overrides: Optional overrides for indicator parameters (for sweeps)

    Returns:
        Tuple of (PortfolioResult, enriched_data dict) where enriched_data maps
        symbol names to their enriched Polars DataFrames with indicators
    """
    logger.info(
        "Portfolio backtest: Loading %d symbols with $%.2f starting capital",
        len(pair_paths),
        starting_equity,
    )

    # Phase 1: Load and enrich ALL symbol data first
    symbol_data: dict[str, pl.DataFrame] = {}

    # Define trailing indicator if needed
    trailing_indicator_def = None
    if risk_config and risk_config.stop_policy.type == "MA_Trailing":
        # e.g. "sma_50" or "ema_200"
        ma_type = risk_config.stop_policy.ma_type.lower()  # "sma" or "ema"
        period = risk_config.stop_policy.ma_period
        param_name = f"{ma_type}_{period}"
        # Store definition for appending to required_indicators
        # Indicator format: IndicatorConfig(name="sma", params={"period": 50}, output_overrides={"sma": "sma_50"})
        # Simplified for calculate_indicators: we might need to manually add to dict if not using metadata
        pass

    for pair, data_path in pair_paths:
        logger.info("Loading data for %s from %s", pair, data_path)

        use_arrow = data_path.suffix.lower() == ".parquet"
        ingestion_result = ingest_ohlcv_data(
            path=data_path,
            timeframe_minutes=1,
            mode="columnar",
            downcast=False,
            use_arrow=use_arrow,
            strict_cadence=False,
            fill_gaps=False,
            return_polars=True,
            show_progress=show_progress,
        )

        enriched_df = ingestion_result.data
        if not isinstance(enriched_df, pl.DataFrame):
            enriched_df = pl.from_pandas(enriched_df)

        # Rename timestamp if needed
        if "timestamp" in enriched_df.columns:
            enriched_df = enriched_df.rename({"timestamp": "timestamp_utc"})

        # Calculate indicators
        strategy = TREND_PULLBACK_STRATEGY
        required_indicators = strategy.metadata.required_indicators

        # Map strategy parameters to indicator overrides
        overrides = {
            "fast_ema": {"period": strategy_params.ema_fast},
            "slow_ema": {"period": strategy_params.ema_slow},
            "atr": {"period": strategy_params.atr_length},
            "rsi": {"period": strategy_params.rsi_length},
        }

        # Apply explicit overrides (e.g. from parameter sweep)
        if indicator_overrides:
            for ind, params in indicator_overrides.items():
                if ind not in overrides:
                    overrides[ind] = {}
                overrides[ind].update(params)

        enriched_df = calculate_indicators(
            enriched_df, required_indicators, overrides=overrides
        )

        symbol_data[pair] = enriched_df
        logger.info(
            "Loaded %s: %d bars, %s to %s",
            pair,
            len(enriched_df),
            enriched_df["timestamp_utc"][0],
            enriched_df["timestamp_utc"][-1],
        )

        # Add dynamic trailing indicator if needed
        if risk_config and risk_config.stop_policy.type == "MA_Trailing":
            ma_type = risk_config.stop_policy.ma_type.lower()  # "sma" or "ema"
            ma_period = risk_config.stop_policy.ma_period
            # Construct indicator string e.g. "sma50" or "ema200"
            ind_str = f"{ma_type}{ma_period}"

            # Override output name to be explicit "sma_50" to match simple logic elsewhere
            overrides = {ind_str: {"output_col": f"{ma_type}_{ma_period}"}}

            ind_df = calculate_indicators(enriched_df, [ind_str], overrides=overrides)

            # Join the new column(s)
            new_cols = [c for c in ind_df.columns if c not in enriched_df.columns]
            if new_cols:
                enriched_df = enriched_df.hstack(ind_df.select(new_cols))

        symbol_data[pair] = enriched_df
    symbol_signals: dict[str, list] = {}

    # Build blackout windows if config provided (Feature 023)
    blackout_windows: list[tuple] = []
    if blackout_config and blackout_config.any_enabled:
        from ..risk.blackout.windows import (
            expand_news_windows,
            expand_session_windows,
            merge_overlapping_windows,
        )
        from ..risk.blackout.calendar import generate_news_calendar

        # Get date range from first symbol's data
        first_df = next(iter(symbol_data.values()))
        data_start = first_df["timestamp_utc"][0]
        data_end = first_df["timestamp_utc"][-1]

        # Build news windows if enabled
        if blackout_config.news.enabled:
            # Convert datetime to date for calendar generation
            start_date = (
                data_start.date() if hasattr(data_start, "date") else data_start
            )
            end_date = data_end.date() if hasattr(data_end, "date") else data_end
            news_events = generate_news_calendar(
                start_date, end_date, blackout_config.news.event_types
            )
            news_windows = expand_news_windows(news_events, blackout_config.news)
            blackout_windows.extend(news_windows)
            logger.info("Built %d news blackout windows", len(news_windows))

        # Build session windows if enabled
        if blackout_config.sessions.enabled:
            session_windows = expand_session_windows(
                data_start, data_end, blackout_config.sessions
            )
            blackout_windows.extend(session_windows)
            logger.info("Built %d session blackout windows", len(session_windows))

        # Build session-only windows if enabled (whitelist approach)
        if blackout_config.session_only.enabled:
            from ..risk.blackout.sessions import build_session_only_blackouts

            start_date = (
                data_start.date() if hasattr(data_start, "date") else data_start
            )
            end_date = data_end.date() if hasattr(data_end, "date") else data_end
            session_only_windows = build_session_only_blackouts(
                start_date, end_date, blackout_config.session_only.allowed_sessions
            )
            # session_only_windows are already tuples, need to convert to BlackoutWindow
            from ..risk.blackout.windows import BlackoutWindow

            for start_utc, end_utc in session_only_windows:
                blackout_windows.append(
                    BlackoutWindow(
                        start_utc=start_utc, end_utc=end_utc, source="session_only"
                    )
                )
            logger.info(
                "Built %d session-only blackout windows for sessions: %s",
                len(session_only_windows),
                blackout_config.session_only.allowed_sessions,
            )

        # Merge overlapping windows, then convert to tuples for filter function
        if blackout_windows:
            merged = merge_overlapping_windows(blackout_windows)
            blackout_windows = [(w.start_utc, w.end_utc) for w in merged]
            logger.info("Total blackout windows after merge: %d", len(blackout_windows))

    for pair, df in symbol_data.items():
        logger.info("Generating signals for %s", pair)

        # Include pair in parameters for position sizing (JPY has different pip value)
        params = strategy_params.model_dump()
        params["pair"] = pair
        signals = generate_signals_vectorized(
            df,
            parameters=params,
            direction_mode=direction_mode.value,
        )

        # Apply blackout filtering if windows exist
        if blackout_windows and signals:
            original_count = len(signals)
            filtered_signals = []

            for signal in signals:
                signal_ts = signal.timestamp_utc
                in_blackout = False

                for start_utc, end_utc in blackout_windows:
                    if start_utc <= signal_ts <= end_utc:
                        in_blackout = True
                        break

                if not in_blackout:
                    filtered_signals.append(signal)

            blocked_count = original_count - len(filtered_signals)
            signals = filtered_signals
            logger.info(
                "Blackout filtering for %s: %d blocked, %d remaining",
                pair,
                blocked_count,
                len(signals),
            )

        symbol_signals[pair] = signals
        logger.info("Generated %d signals for %s", len(signals), pair)

    # Phase 3: Run portfolio simulation
    simulator = PortfolioSimulator(
        starting_equity=starting_equity,
        risk_per_trade=0.0025,  # 0.25%
        max_positions_per_symbol=1,
        target_r_mult=strategy_params.target_r_mult,
        risk_config=risk_config,
    )

    run_id = (
        f"portfolio_{direction_mode.value.lower()}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )

    result = simulator.simulate(
        symbol_data=symbol_data,
        symbol_signals=symbol_signals,
        direction_mode=direction_mode.value,
        run_id=run_id,
        timeframe=timeframe,
    )

    return result, symbol_data


def run_multi_symbol_backtest(
    pair_paths: list[tuple[str, Path]],
    direction_mode: DirectionMode,
    strategy_params,
    dry_run: bool = False,
    enable_profiling: bool = False,
    show_progress: bool = True,
    timeframe: str = "1m",
):
    """Run backtests on multiple symbols and aggregate results.

    Executes independent backtests for each symbol, then aggregates results
    into a multi-symbol BacktestResult with combined PnL calculation.

    Args:
        pair_paths: List of (pair, path) tuples from construct_data_paths()
        direction_mode: Direction mode (LONG/SHORT/BOTH)
        strategy_params: Strategy parameters to use
        dry_run: If True, generate signals only without execution
        enable_profiling: If True, enable performance profiling
        show_progress: If True, show progress bars

    Returns:
        Tuple of (Multi-symbol BacktestResult, enriched_data dict with DataFrames)
    """
    results: dict[str, "BacktestResult"] = {}
    enriched_data: dict[str, pl.DataFrame] = {}  # For visualization
    failures: list[dict] = []
    all_signals: list = []
    all_executions: list = []
    total_r_multiple = 0.0

    # Equal capital allocation per symbol
    num_symbols = len(pair_paths)
    capital_per_symbol = DEFAULT_ACCOUNT_BALANCE / num_symbols

    logger.info(
        "Starting multi-symbol backtest for %d symbols with $%.2f each",
        num_symbols,
        capital_per_symbol,
    )

    # Run backtest for each symbol
    for pair, data_path in pair_paths:
        logger.info("Processing symbol: %s from %s", pair, data_path)

        try:
            # Load data using Polars
            use_arrow = data_path.suffix.lower() == ".parquet"
            ingestion_result = ingest_ohlcv_data(
                path=data_path,
                timeframe_minutes=1,
                mode="columnar",
                downcast=False,
                use_arrow=use_arrow,
                strict_cadence=False,
                fill_gaps=False,
                return_polars=True,
                show_progress=show_progress,
            )

            enriched_df = ingestion_result.data
            if not isinstance(enriched_df, pl.DataFrame):
                enriched_df = pl.from_pandas(enriched_df)

            # Rename timestamp if needed
            if "timestamp" in enriched_df.columns:
                enriched_df = enriched_df.rename({"timestamp": "timestamp_utc"})

            # Calculate indicators
            strategy = TREND_PULLBACK_STRATEGY
            required_indicators = strategy.metadata.required_indicators

            # Map strategy parameters to indicator overrides
            overrides = {
                "fast_ema": {"period": strategy_params.ema_fast},
                "slow_ema": {"period": strategy_params.ema_slow},
                "atr": {"period": strategy_params.atr_length},
                "rsi": {"period": strategy_params.rsi_length},
            }

            enriched_df = calculate_indicators(
                enriched_df, required_indicators, overrides=overrides
            )

            # Create orchestrator
            orchestrator = BacktestOrchestrator(
                direction_mode=direction_mode,
                dry_run=dry_run,
                enable_profiling=enable_profiling,
                enable_progress=show_progress,
            )

            # Run backtest

            run_id = (
                f"{pair.lower()}_{direction_mode.value.lower()}_"
                f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            )

            result = orchestrator.run_backtest(
                candles=enriched_df,
                pair=pair,
                run_id=run_id,
                strategy=strategy,
                **strategy_params.model_dump(),
            )

            results[pair] = result
            enriched_data[pair] = enriched_df  # Store for visualization

            # Aggregate signals and executions
            if result.signals:
                all_signals.extend(result.signals)
            if result.executions:
                all_executions.extend(result.executions)

            # Calculate R-multiple contribution for this symbol
            if result.metrics:
                if hasattr(result.metrics, "combined"):
                    total_r_multiple += result.metrics.combined.avg_r * (
                        result.metrics.combined.trade_count or 0
                    )
                elif hasattr(result.metrics, "avg_r"):
                    total_r_multiple += result.metrics.avg_r * (
                        result.metrics.trade_count or 0
                    )

            logger.info(
                "Completed %s: %d trades",
                pair,
                (
                    (
                        result.metrics.combined.trade_count
                        if hasattr(result.metrics, "combined")
                        else result.metrics.trade_count
                    )
                    if result.metrics
                    else 0
                ),
            )

        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            logger.warning("Backtest failed for %s: %s", pair, exc)
            failures.append({"pair": pair, "error": str(exc)})
            continue

    # Aggregate into multi-symbol BacktestResult

    if not results:
        raise RuntimeError("All symbol backtests failed")

    # Get time bounds from first successful result
    first_result = next(iter(results.values()))

    # Build aggregated metrics
    total_trades = sum(
        (
            r.metrics.combined.trade_count
            if hasattr(r.metrics, "combined")
            else r.metrics.trade_count
        )
        for r in results.values()
        if r.metrics
    )

    _avg_win_rate = (  # Reserved for future aggregate reporting
        sum(
            (
                r.metrics.combined.win_rate
                if hasattr(r.metrics, "combined")
                else r.metrics.win_rate
            )
            for r in results.values()
            if r.metrics
        )
        / len(results)
        if results
        else 0.0
    )

    # Create aggregated result
    multi_result = BacktestResult(
        run_id=f"multi_{direction_mode.value.lower()}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        direction_mode=direction_mode.value,
        start_time=first_result.start_time,
        end_time=datetime.now(timezone.utc),
        data_start_date=first_result.data_start_date,
        data_end_date=first_result.data_end_date,
        total_candles=sum(r.total_candles for r in results.values()),
        metrics=first_result.metrics,  # Use first result's metrics structure
        pair=None,  # Multi-symbol has no single pair
        timeframe=timeframe,  # FR-015: Include timeframe in output
        symbols=list(results.keys()),
        results=results,
        failures=failures if failures else None,
        signals=all_signals if all_signals else None,
        executions=all_executions if all_executions else None,
        dry_run=dry_run,
    )

    logger.info(
        "Multi-symbol backtest complete: %d symbols, %d trades, %d failures",
        len(results),
        total_trades,
        len(failures),
    )

    return multi_result, enriched_data
