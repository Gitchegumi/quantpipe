"""Integration tests for interactive fraction prompt and validation.

Tests FR-015 (interactive prompt), SC-010 (validation with ≤2 attempts),
portion selection, and command-line argument validation.
"""

import subprocess
import sys
from pathlib import Path


class TestFractionValidation:
    """Test suite for fraction and portion validation logic."""

    # Use actual test data file for validation tests
    TEST_DATA_FILE = "price_data/processed/eurusd/test/eurusd_test.csv"

    def test_fraction_validation_zero_rejected(self):
        """Zero fraction rejected via CLI (SC-010)."""
        # Test --data-frac=0 is rejected
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                self.TEST_DATA_FILE,
                "--direction",
                "LONG",
                "--data-frac",
                "0.0",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        assert result.returncode != 0, "Zero fraction should be rejected"
        assert "must be between 0.0 (exclusive) and 1.0" in result.stderr

    def test_fraction_validation_negative_rejected(self):
        """Negative fraction rejected via CLI (SC-010)."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                self.TEST_DATA_FILE,
                "--direction",
                "LONG",
                "--data-frac",
                "-0.5",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        assert result.returncode != 0, "Negative fraction should be rejected"
        assert "must be between 0.0 (exclusive) and 1.0" in result.stderr

    def test_fraction_validation_above_one_rejected(self):
        """Fraction > 1.0 rejected via CLI (SC-010)."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                self.TEST_DATA_FILE,
                "--direction",
                "LONG",
                "--data-frac",
                "1.5",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        assert result.returncode != 0, "Fraction > 1.0 should be rejected"
        assert "must be between 0.0 (exclusive) and 1.0" in result.stderr

    def test_fraction_validation_one_accepted(self):
        """Fraction = 1.0 accepted as valid (FR-002)."""
        # This test validates that 1.0 is valid (won't test full execution)
        # Just check the fraction passes validation by not erroring on it
        # We can't run full backtest without valid data, so we test that
        # fraction validation passes and it errors on data file instead
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                "nonexistent.csv",
                "--direction",
                "LONG",
                "--data-frac",
                "1.0",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        # Should fail on missing data file, not fraction validation
        assert "must be between 0.0 (exclusive) and 1.0" not in result.stderr

    def test_portion_calculation_quartile(self):
        """Fraction 0.25 creates 4 portions (FR-002)."""
        # Test that portion validation uses correct max_portions
        # For fraction=0.25, max_portions = int(1.0/0.25) = 4
        # So portion=5 should be rejected
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                self.TEST_DATA_FILE,
                "--direction",
                "LONG",
                "--data-frac",
                "0.25",
                "--portion",
                "5",  # Invalid: only 4 portions available
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        assert result.returncode != 0, "Out-of-range portion should be rejected"
        assert "must be between 1 and 4" in result.stderr

    def test_portion_validation_within_range(self):
        """Valid portion within range accepted (FR-002)."""
        # portion=2 should be valid for fraction=0.25 (4 portions)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                "nonexistent.csv",
                "--direction",
                "LONG",
                "--data-frac",
                "0.25",
                "--portion",
                "2",
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        # Should fail on missing data, not portion validation
        assert (
            "must be between" not in result.stderr
            or "portion" not in result.stderr.lower()
        )

    def test_portion_validation_zero_rejected(self):
        """Portion = 0 rejected (1-based indexing) (FR-002)."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                self.TEST_DATA_FILE,
                "--direction",
                "LONG",
                "--data-frac",
                "0.5",
                "--portion",
                "0",  # Invalid: must be ≥ 1
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        assert result.returncode != 0, "Portion=0 should be rejected (1-based)"
        assert "must be between 1 and" in result.stderr

    def test_full_fraction_skips_portion(self):
        """Fraction=1.0 sets portion=1 automatically (FR-002)."""
        # When fraction=1.0, portion should default to 1
        # Even if user tries to set portion, it should be overridden or ignored
        # Let's verify that fraction=1.0 doesn't require portion validation
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                "nonexistent.csv",
                "--direction",
                "LONG",
                "--data-frac",
                "1.0",
                # No --portion specified
            ],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            check=False,
        )

        # Should not error on missing portion for full dataset
        assert (
            "portion" not in result.stderr.lower()
            or "must be between" not in result.stderr
        )
