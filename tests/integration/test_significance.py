"""Statistical significance test harness for backtest results.

This module provides utilities to assess whether trading strategy performance
metrics are statistically significant or could be attributed to random chance.
Uses bootstrap resampling and permutation tests to compute p-values.
"""

import random
from typing import List, Tuple

import numpy as np
import pytest

from src.models.core import TradeExecution


def compute_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """Compute Sharpe ratio from list of returns.

    Args:
        returns: List of trade returns (R-multiples or percentages)
        risk_free_rate: Annualized risk-free rate (default 0.0)

    Returns:
        Sharpe ratio (mean excess return / std dev of returns)
        Returns 0.0 if insufficient data or zero variance
    """
    if len(returns) < 2:
        return 0.0

    arr = np.array(returns)
    mean_return = np.mean(arr)
    std_return = np.std(arr, ddof=1)

    if std_return == 0.0:
        return 0.0

    return (mean_return - risk_free_rate) / std_return


def compute_expectancy(returns: List[float]) -> float:
    """Compute expectancy (average R-multiple per trade).

    Args:
        returns: List of trade returns in R-multiples

    Returns:
        Mean return value, or 0.0 if no trades
    """
    if len(returns) == 0:
        return 0.0
    return float(np.mean(returns))


def bootstrap_sharpe_p_value(
    returns: List[float], n_iterations: int = 10000, seed: int = 42
) -> float:
    """Compute p-value for Sharpe ratio using bootstrap resampling.

    Tests null hypothesis that true Sharpe ratio <= 0 (no edge).

    Args:
        returns: Observed trade returns
        n_iterations: Number of bootstrap samples
        seed: Random seed for reproducibility

    Returns:
        p-value: proportion of bootstrap samples with Sharpe <= 0
        Lower p-value indicates stronger evidence of positive edge
    """
    if len(returns) < 2:
        return 1.0

    random.seed(seed)
    np.random.seed(seed)

    observed_sharpe = compute_sharpe_ratio(returns)

    # Bootstrap: resample with replacement
    null_sharpe_values = []
    for _ in range(n_iterations):
        resampled = np.random.choice(returns, size=len(returns), replace=True)
        sharpe = compute_sharpe_ratio(resampled.tolist())
        null_sharpe_values.append(sharpe)

    # Compute p-value: proportion of samples <= 0
    count_le_zero = sum(1 for s in null_sharpe_values if s <= 0)
    p_value = count_le_zero / n_iterations

    return p_value


def permutation_test_expectancy(
    returns: List[float], n_iterations: int = 10000, seed: int = 42
) -> float:
    """Compute p-value for expectancy using permutation test.

    Tests null hypothesis that true expectancy <= 0 (no edge).

    Args:
        returns: Observed trade returns
        n_iterations: Number of permutation samples
        seed: Random seed for reproducibility

    Returns:
        p-value: proportion of permutations with expectancy <= 0
        Lower p-value indicates stronger evidence of positive edge
    """
    if len(returns) == 0:
        return 1.0

    random.seed(seed)
    np.random.seed(seed)

    observed_expectancy = compute_expectancy(returns)

    # Permutation test: randomly flip signs
    null_expectancy_values = []
    for _ in range(n_iterations):
        signs = np.random.choice([-1, 1], size=len(returns))
        permuted = np.array(returns) * signs
        expectancy = compute_expectancy(permuted.tolist())
        null_expectancy_values.append(expectancy)

    # Compute p-value: proportion of samples <= 0
    count_le_zero = sum(1 for e in null_expectancy_values if e <= 0)
    p_value = count_le_zero / n_iterations

    return p_value


def assess_statistical_significance(
    executions: List[TradeExecution], alpha: float = 0.05
) -> Tuple[bool, dict]:
    """Assess whether backtest results are statistically significant.

    Args:
        executions: List of trade executions
        alpha: Significance level (default 0.05 for 95% confidence)

    Returns:
        Tuple of (is_significant, details_dict)
        - is_significant: True if p-value < alpha for both Sharpe and expectancy
        - details_dict: Contains p_value_sharpe, p_value_expectancy, sample_size
    """
    if len(executions) == 0:
        return False, {
            "p_value_sharpe": 1.0,
            "p_value_expectancy": 1.0,
            "sample_size": 0,
            "message": "No trades executed",
        }

    # Extract R-multiples from executions
    returns = [ex.r_multiple for ex in executions if ex.r_multiple is not None]

    if len(returns) < 2:
        return False, {
            "p_value_sharpe": 1.0,
            "p_value_expectancy": 1.0,
            "sample_size": len(returns),
            "message": "Insufficient trades for significance testing",
        }

    # Compute p-values
    p_sharpe = bootstrap_sharpe_p_value(returns)
    p_expectancy = permutation_test_expectancy(returns)

    # Both must be significant
    is_significant = p_sharpe < alpha and p_expectancy < alpha

    details = {
        "p_value_sharpe": p_sharpe,
        "p_value_expectancy": p_expectancy,
        "sample_size": len(returns),
        "alpha": alpha,
        "sharpe_significant": p_sharpe < alpha,
        "expectancy_significant": p_expectancy < alpha,
    }

    return is_significant, details


# ============================================================================
# Test Cases
# ============================================================================


def test_compute_sharpe_ratio_positive_returns():
    """Test Sharpe ratio computation with consistently positive returns."""
    returns = [1.0, 1.5, 0.8, 1.2, 1.3]
    sharpe = compute_sharpe_ratio(returns)
    assert sharpe > 0, "Positive returns should yield positive Sharpe"


def test_compute_sharpe_ratio_zero_variance():
    """Test Sharpe ratio with identical returns (zero variance)."""
    returns = [1.0, 1.0, 1.0, 1.0]
    sharpe = compute_sharpe_ratio(returns)
    assert sharpe == 0.0, "Zero variance should return Sharpe = 0"


def test_compute_sharpe_ratio_insufficient_data():
    """Test Sharpe ratio with insufficient sample size."""
    returns = [1.0]
    sharpe = compute_sharpe_ratio(returns)
    assert sharpe == 0.0, "Single return should yield Sharpe = 0"


def test_compute_expectancy_positive():
    """Test expectancy computation with positive average."""
    returns = [1.0, 2.0, -0.5, 1.5]
    expectancy = compute_expectancy(returns)
    assert expectancy == 1.0, "Average of [1, 2, -0.5, 1.5] = 1.0"


def test_compute_expectancy_empty():
    """Test expectancy with no trades."""
    returns = []
    expectancy = compute_expectancy(returns)
    assert expectancy == 0.0, "Empty list should yield expectancy = 0"


def test_bootstrap_sharpe_p_value_strong_edge():
    """Test bootstrap p-value with strong positive edge."""
    # Consistently positive returns
    returns = [1.0, 1.2, 0.9, 1.1, 1.3, 1.0, 1.2, 1.1, 0.95, 1.15]
    p_value = bootstrap_sharpe_p_value(returns, n_iterations=1000, seed=42)
    assert p_value < 0.05, "Strong edge should yield low p-value"


def test_bootstrap_sharpe_p_value_no_edge():
    """Test bootstrap p-value with zero-mean returns."""
    # Random returns centered on zero
    random.seed(42)
    returns = [random.gauss(0, 1) for _ in range(20)]
    p_value = bootstrap_sharpe_p_value(returns, n_iterations=1000, seed=42)
    assert p_value > 0.05, "No edge should yield high p-value"


def test_bootstrap_sharpe_p_value_insufficient_data():
    """Test bootstrap with single trade."""
    returns = [1.0]
    p_value = bootstrap_sharpe_p_value(returns, n_iterations=100, seed=42)
    assert p_value == 1.0, "Single trade should return p-value = 1.0"


def test_permutation_test_expectancy_positive_edge():
    """Test permutation test with consistently positive expectancy."""
    returns = [1.0, 1.5, 0.8, 1.2, 1.3, 1.1, 1.4]
    p_value = permutation_test_expectancy(returns, n_iterations=1000, seed=42)
    assert p_value < 0.05, "Positive expectancy should yield low p-value"


def test_permutation_test_expectancy_no_edge():
    """Test permutation test with symmetric returns."""
    returns = [-1.0, 1.0, -0.5, 0.5, -1.2, 1.2]
    p_value = permutation_test_expectancy(returns, n_iterations=1000, seed=42)
    assert p_value > 0.05, "Symmetric returns should yield high p-value"


def test_permutation_test_expectancy_empty():
    """Test permutation test with no trades."""
    returns = []
    p_value = permutation_test_expectancy(returns, n_iterations=100, seed=42)
    assert p_value == 1.0, "Empty returns should yield p-value = 1.0"


def test_assess_significance_strong_edge():
    """Test significance assessment with strong positive edge."""
    # Create mock executions with strong positive R-multiples
    executions = [
        TradeExecution(
            signal_id=f"sig_{i}",
            entry_timestamp=None,
            entry_price=100.0,
            exit_timestamp=None,
            exit_price=105.0,
            stop_price=99.0,
            position_size=1.0,
            r_multiple=1.0 + i * 0.1,
            exit_reason="target",
        )
        for i in range(10)
    ]

    is_sig, details = assess_statistical_significance(executions, alpha=0.05)
    assert is_sig is True, "Strong edge should be statistically significant"
    assert details["p_value_sharpe"] < 0.05
    assert details["p_value_expectancy"] < 0.05
    assert details["sample_size"] == 10


def test_assess_significance_no_trades():
    """Test significance assessment with zero trades."""
    executions = []
    is_sig, details = assess_statistical_significance(executions, alpha=0.05)
    assert is_sig is False, "No trades should not be significant"
    assert details["sample_size"] == 0
    assert "No trades" in details["message"]


def test_assess_significance_insufficient_trades():
    """Test significance assessment with single trade."""
    executions = [
        TradeExecution(
            signal_id="sig_1",
            entry_timestamp=None,
            entry_price=100.0,
            exit_timestamp=None,
            exit_price=105.0,
            stop_price=99.0,
            position_size=1.0,
            r_multiple=5.0,
            exit_reason="target",
        )
    ]

    is_sig, details = assess_statistical_significance(executions, alpha=0.05)
    assert is_sig is False, "Single trade should not be significant"
    assert details["sample_size"] == 1
    assert "Insufficient" in details["message"]


def test_assess_significance_mixed_results():
    """Test significance with mixed positive/negative returns."""
    # Some positive, some negative - weak edge
    random.seed(42)
    executions = [
        TradeExecution(
            signal_id=f"sig_{i}",
            entry_timestamp=None,
            entry_price=100.0,
            exit_timestamp=None,
            exit_price=100.0,
            stop_price=99.0,
            position_size=1.0,
            r_multiple=random.gauss(0.2, 1.0),  # Slight positive bias
            exit_reason="target",
        )
        for i in range(30)
    ]

    is_sig, details = assess_statistical_significance(executions, alpha=0.05)
    # With weak edge and noise, may or may not be significant
    assert "p_value_sharpe" in details
    assert "p_value_expectancy" in details
    assert details["sample_size"] == 30
