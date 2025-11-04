"""Unit tests for abort criteria evaluation."""

from src.backtest.abort import (
    evaluate_global_abort,
    should_halt_strategy,
    AbortReason,
)


def test_global_drawdown_breach_triggers_abort():
    """Global drawdown exceeding limit should trigger abort."""
    should_abort, reason = evaluate_global_abort(
        current_portfolio_drawdown=0.12,
        global_drawdown_limit=0.10,
    )
    assert should_abort is True
    assert reason == AbortReason.GLOBAL_DRAWDOWN_BREACH


def test_global_drawdown_within_limit_no_abort():
    """Global drawdown within limit should not trigger abort."""
    should_abort, reason = evaluate_global_abort(
        current_portfolio_drawdown=0.08,
        global_drawdown_limit=0.10,
    )
    assert should_abort is False
    assert reason == AbortReason.NO_ABORT


def test_no_global_limit_configured_no_abort():
    """No global drawdown limit configured should not trigger abort."""
    should_abort, reason = evaluate_global_abort(
        current_portfolio_drawdown=0.50,
        global_drawdown_limit=None,
    )
    assert should_abort is False
    assert reason == AbortReason.NO_ABORT


def test_data_integrity_failure_triggers_abort():
    """Data integrity failure should trigger unrecoverable error abort."""
    should_abort, reason = evaluate_global_abort(
        current_portfolio_drawdown=0.05,
        global_drawdown_limit=0.10,
        data_integrity_ok=False,
    )
    assert should_abort is True
    assert reason == AbortReason.UNRECOVERABLE_ERROR


def test_data_integrity_ok_no_abort():
    """Data integrity OK should not trigger abort."""
    should_abort, reason = evaluate_global_abort(
        current_portfolio_drawdown=0.05,
        global_drawdown_limit=0.10,
        data_integrity_ok=True,
    )
    assert should_abort is False
    assert reason == AbortReason.NO_ABORT


def test_strategy_halt_on_local_breach():
    """Strategy drawdown exceeding local limit should halt."""
    should_halt = should_halt_strategy(
        strategy_name="alpha",
        current_drawdown=0.12,
        per_strategy_limit=0.10,
    )
    assert should_halt is True


def test_strategy_continue_within_limit():
    """Strategy drawdown within limit should continue."""
    should_halt = should_halt_strategy(
        strategy_name="beta",
        current_drawdown=0.08,
        per_strategy_limit=0.10,
    )
    assert should_halt is False


def test_strategy_halt_at_exact_limit():
    """Strategy drawdown at exact limit should not halt (> not >=)."""
    should_halt = should_halt_strategy(
        strategy_name="gamma",
        current_drawdown=0.10,
        per_strategy_limit=0.10,
    )
    assert should_halt is False
