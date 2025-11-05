"""Unit tests for fidelity comparison utilities."""

# pylint: disable=unused-import

import pytest
from src.backtest.fidelity import compare_fidelity, FidelityReport


class TestCompareFidelity:
    """Tests for fidelity comparison between baseline and optimized results."""

    def test_exact_match_passes(self):
        """Exact match between baseline and optimized should pass."""
        baseline = [
            {
                "exit_price": 1.1000,
                "pnl": 0.02,
                "exit_index": 100,
                "holding_duration": 10,
            }
        ]
        optimized = [
            {
                "exit_price": 1.1000,
                "pnl": 0.02,
                "exit_index": 100,
                "holding_duration": 10,
            }
        ]

        report = compare_fidelity(baseline, optimized)

        assert report.passed is True
        assert report.total_comparisons == 1
        assert report.price_violations == 0
        assert report.pnl_violations == 0
        assert report.index_violations == 0
        assert report.duration_violations == 0
        assert len(report.details) == 0

    def test_price_within_tolerance_passes(self):
        """Price differences within tolerance should pass."""
        baseline = [{"exit_price": 1.1000000}]
        optimized = [{"exit_price": 1.1000005}]  # 5e-7 difference

        report = compare_fidelity(baseline, optimized, price_tolerance=1e-6)

        assert report.passed is True
        assert report.price_violations == 0

    def test_price_exceeds_tolerance_fails(self):
        """Price differences exceeding tolerance should fail."""
        baseline = [{"exit_price": 1.1000}]
        optimized = [{"exit_price": 1.1002}]  # 2e-4 difference

        report = compare_fidelity(baseline, optimized, price_tolerance=1e-6)

        assert report.passed is False
        assert report.price_violations == 1
        assert len(report.details) == 1
        assert "price diff" in report.details[0]

    def test_pnl_within_tolerance_passes(self):
        """PnL differences within tolerance should pass."""
        baseline = [{"pnl": 0.0200}]
        optimized = [{"pnl": 0.0201}]  # 0.01% difference

        report = compare_fidelity(baseline, optimized, pnl_tolerance=0.0001)

        assert report.passed is True
        assert report.pnl_violations == 0

    def test_pnl_exceeds_tolerance_fails(self):
        """PnL differences exceeding tolerance should fail."""
        baseline = [{"pnl": 0.0200}]
        optimized = [{"pnl": 0.0250}]  # 0.5% difference

        report = compare_fidelity(baseline, optimized, pnl_tolerance=0.0001)

        assert report.passed is False
        assert report.pnl_violations == 1
        assert "PnL diff" in report.details[0]

    def test_exit_index_exact_match_required(self):
        """Exit indices must match exactly."""
        baseline = [{"exit_index": 100}]
        optimized = [{"exit_index": 101}]

        report = compare_fidelity(baseline, optimized)

        assert report.passed is False
        assert report.index_violations == 1
        assert "exit index mismatch" in report.details[0]

    def test_duration_within_tolerance_passes(self):
        """Duration differences within tolerance should pass."""
        baseline = [{"holding_duration": 10}]
        optimized = [{"holding_duration": 11}]  # 1 bar difference

        report = compare_fidelity(baseline, optimized, duration_tolerance=1)

        assert report.passed is True
        assert report.duration_violations == 0

    def test_duration_exceeds_tolerance_fails(self):
        """Duration differences exceeding tolerance should fail."""
        baseline = [{"holding_duration": 10}]
        optimized = [{"holding_duration": 15}]  # 5 bars difference

        report = compare_fidelity(baseline, optimized, duration_tolerance=1)

        assert report.passed is False
        assert report.duration_violations == 1
        assert "duration diff" in report.details[0]

    def test_count_mismatch_fails(self):
        """Mismatched trade counts should fail immediately."""
        baseline = [{"exit_price": 1.1000}, {"exit_price": 1.1010}]
        optimized = [{"exit_price": 1.1000}]

        report = compare_fidelity(baseline, optimized)

        assert report.passed is False
        assert report.total_comparisons == 0
        assert "Trade count mismatch" in report.details[0]

    def test_multiple_violations_all_reported(self):
        """Multiple violations should all be captured."""
        baseline = [
            {
                "exit_price": 1.1000,
                "pnl": 0.02,
                "exit_index": 100,
                "holding_duration": 10,
            }
        ]
        optimized = [
            {
                "exit_price": 1.1010,  # Price violation
                "pnl": 0.03,  # PnL violation
                "exit_index": 101,  # Index violation
                "holding_duration": 20,  # Duration violation
            }
        ]

        report = compare_fidelity(
            baseline,
            optimized,
            price_tolerance=1e-6,
            pnl_tolerance=0.0001,
            duration_tolerance=1,
        )

        assert report.passed is False
        assert report.price_violations == 1
        assert report.pnl_violations == 1
        assert report.index_violations == 1
        assert report.duration_violations == 1
        assert len(report.details) == 4

    def test_empty_lists_pass(self):
        """Empty result sets should pass."""
        report = compare_fidelity([], [])

        assert report.passed is True
        assert report.total_comparisons == 0

    def test_missing_fields_handled_gracefully(self):
        """Missing optional fields should not cause errors."""
        baseline = [{"exit_price": 1.1000}]
        optimized = [{"pnl": 0.02}]

        report = compare_fidelity(baseline, optimized)

        assert report.passed is True  # No comparable fields, no violations
        assert report.total_comparisons == 1

    def test_multiple_trades_comparison(self):
        """Should handle multiple trades correctly."""
        baseline = [
            {"exit_price": 1.1000, "exit_index": 100},
            {"exit_price": 1.1010, "exit_index": 200},
            {"exit_price": 1.1020, "exit_index": 300},
        ]
        optimized = [
            {"exit_price": 1.1000, "exit_index": 100},
            {"exit_price": 1.1010, "exit_index": 200},
            {"exit_price": 1.1020, "exit_index": 300},
        ]

        report = compare_fidelity(baseline, optimized)

        assert report.passed is True
        assert report.total_comparisons == 3
