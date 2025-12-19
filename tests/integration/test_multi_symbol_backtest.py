"""
Integration tests for multi-symbol backtest functionality.

Tests cover:
- Multi-symbol execution (both pairs run)
- Aggregated PnL computation
- Default account balance usage
- Single-symbol regression protection
- Parquet pipeline verification

Feature: 013-multi-symbol-backtest
"""

import pytest


class TestMultiSymbolExecution:
    """Tests for multi-symbol backtest execution (US1)."""

    def test_multi_symbol_both_pairs_executed(self):
        """T021: Verify both symbols execute when multiple pairs specified."""
        # TODO: Implement in T021
        pytest.skip("Pending implementation in T021")

    def test_multi_symbol_aggregated_pnl(self):
        """T022: Verify combined PnL reflects concurrent trading."""
        # TODO: Implement in T022
        pytest.skip("Pending implementation in T022")

    def test_multi_symbol_default_balance(self):
        """T023: Verify default $2,500 balance is used."""
        # TODO: Implement in T023
        pytest.skip("Pending implementation in T023")

    def test_single_symbol_unchanged(self):
        """T024: Verify single-symbol behavior unchanged (regression)."""
        # TODO: Implement in T024
        pytest.skip("Pending implementation in T024")


class TestParquetPipeline:
    """Tests for Parquet pipeline verification (US3)."""

    def test_parquet_end_to_end_pipeline(self):
        """T025: Verify Parquet files work through entire pipeline."""
        # TODO: Implement in T025
        pytest.skip("Pending implementation in T025")

    def test_parquet_fallback_to_csv(self):
        """T026: Verify CSV fallback when Parquet missing."""
        # TODO: Implement in T026
        pytest.skip("Pending implementation in T026")

    def test_progress_bars_clean_display(self):
        """T027: Verify progress bars display cleanly."""
        # TODO: Implement in T027
        pytest.skip("Pending implementation in T027")
