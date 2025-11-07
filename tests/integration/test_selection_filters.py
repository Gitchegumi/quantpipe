"""Integration tests for CLI symbol selection and filtering (Phase 6: US4, T045).

Tests verify --portfolio-mode and --disable-symbol CLI arguments correctly
route to appropriate runners and filter symbols as expected.

Success criteria:
- --portfolio-mode='independent' routes to IndependentRunner
- --portfolio-mode='portfolio' routes to PortfolioOrchestrator
- --disable-symbol excludes specified symbols from execution
- Validation errors produce clear messages

Refs: FR-002 (symbol selection), FR-003 (execution modes), FR-007 (validation)
"""

import subprocess
import sys


class TestPortfolioModeSelection:
    """Test --portfolio-mode flag routes to correct execution engine."""

    def test_independent_mode_default(self, tmp_path):
        """Verify independent mode is default for multi-symbol runs."""
        # Create minimal fixture data (will fail early, just checking mode selection)
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        # Run with multiple pairs (no --portfolio-mode specified)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        # Combine stdout and stderr for searching
        output = result.stdout + result.stderr

        # Should log "Portfolio mode: independent" (default)
        assert "Portfolio mode: independent" in output or (
            "independent" in output.lower()
        ), f"Expected independent mode to be default. Output: {output}"

    def test_portfolio_mode_explicit(self, tmp_path):
        """Verify --portfolio-mode=portfolio routes to PortfolioOrchestrator."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--portfolio-mode",
                "portfolio",
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should attempt PortfolioOrchestrator (or at least log portfolio mode)
        assert (
            "Portfolio mode: portfolio" in output
            or "portfolio multi-symbol" in output.lower()
        ), f"Expected portfolio mode selection in logs. Output: {output}"

        # Note: May abort early if no valid symbols, which is acceptable for this test
        # The key is that portfolio mode was selected, not necessarily executed


class TestSymbolDisabling:
    """Test --disable-symbol flag filters symbols correctly."""

    def test_disable_symbol_filters_before_validation(self, tmp_path):
        """Verify --disable-symbol removes symbols before validation."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "USDJPY",
                "--disable-symbol",
                "GBPUSD",
                "--direction",
                "LONG",
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should log filtered symbols
        assert (
            "Filtered out 1 disabled symbol" in output
            or "disabled symbol" in output.lower()
        ), f"Expected disabled symbol logging. Output: {output}"

    def test_disable_all_symbols_aborts(self, tmp_path):
        """Verify disabling all symbols produces clear error."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--disable-symbol",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should exit with error about no remaining symbols
        assert result.returncode != 0, "Expected non-zero exit code"
        assert (
            "no symbols remaining" in output.lower() or "aborting" in output.lower()
        ), f"Expected clear error message about no symbols remaining. Output: {output}"


class TestModeValidation:
    """Test validation of portfolio-mode-specific arguments."""

    def test_correlation_threshold_warns_for_independent_mode(self, tmp_path):
        """Verify --correlation-threshold warns when not in portfolio mode."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--portfolio-mode",
                "independent",
                "--correlation-threshold",
                "0.8",
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should warn that threshold only applies to portfolio mode
        #  (warning may be formatted across multiple lines)
        assert (
            "--correlation-threshold" in output and "ignoring" in output.lower()
        ) or "only applies to portfolio mode" in output.lower(), (
            f"Expected warning about threshold in independent mode. Output: {output}"
        )

    def test_snapshot_interval_warns_for_independent_mode(self, tmp_path):
        """Verify --snapshot-interval warns when not in portfolio mode."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--portfolio-mode",
                "independent",
                "--snapshot-interval",
                "10",
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should warn that interval only applies to portfolio mode
        # (warning may be formatted across multiple lines)
        assert (
            "--snapshot-interval" in output and "ignoring" in output.lower()
        ) or "only applies to portfolio mode" in output.lower(), (
            f"Expected warning about interval in independent mode. Output: {output}"
        )

    def test_correlation_threshold_out_of_range_errors(self, tmp_path):
        """Verify invalid correlation threshold produces error."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--portfolio-mode",
                "portfolio",
                "--correlation-threshold",
                "1.5",  # Invalid: > 1.0
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should exit with clear error
        assert result.returncode != 0, "Expected non-zero exit code"
        assert (
            "must be between 0.0 and 1.0" in output
        ), f"Expected range validation error. Output: {output}"

    def test_snapshot_interval_negative_errors(self, tmp_path):
        """Verify negative snapshot interval produces error."""
        data_file = tmp_path / "test.csv"
        data_file.write_text(
            "timestamp_utc,open,high,low,close,volume\n"
            "2024-01-01 00:00:00,1.0,1.0,1.0,1.0,100\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.cli.run_backtest",
                "--data",
                str(data_file),
                "--pair",
                "EURUSD",
                "GBPUSD",
                "--direction",
                "LONG",
                "--portfolio-mode",
                "portfolio",
                "--snapshot-interval",
                "-10",  # Invalid: negative
                "--data-frac",
                "1.0",  # Skip interactive prompt
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr

        # Should exit with clear error
        assert result.returncode != 0, "Expected non-zero exit code"
        assert (
            "must be positive" in output
        ), f"Expected positive validation error. Output: {output}"
