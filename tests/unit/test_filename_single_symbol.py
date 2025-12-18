"""Unit tests for single-symbol filename pattern.

Feature: 008-multi-symbol
Task: T015 - Verify filename pattern unchanged for single-symbol run
User Story: US1 - Single Symbol Regression
"""

import re
from datetime import UTC, datetime

from src.data_io.formatters import generate_output_filename
from src.models.enums import DirectionMode, OutputFormat


class TestSingleSymbolFilenamePattern:
    """Test filename generation for single-symbol backtests."""

    def test_filename_without_symbol_tag_legacy(self):
        """Test legacy filename format without symbol tag.

        For backward compatibility, single-symbol runs without explicit
        symbol tag should generate filenames without symbol component.
        """
        timestamp = datetime(2025, 11, 6, 14, 30, 45, tzinfo=UTC)

        # Test without symbol_tag (legacy format)
        filename = generate_output_filename(
            direction=DirectionMode.LONG,
            output_format=OutputFormat.TEXT,
            timestamp=timestamp,
            symbol_tag=None,
        )

        # Should match: backtest_{direction}_{YYYYMMDD}_{HHMMSS}.txt
        pattern = r"^backtest_long_\d{8}_\d{6}\.txt$"
        assert re.match(
            pattern, filename
        ), f"Filename '{filename}' does not match expected pattern"
        assert filename == "backtest_long_20251106_143045.txt"

    def test_filename_with_symbol_tag(self):
        """Test new filename format with symbol tag.

        Multi-symbol feature adds symbol tag support, but it should work
        for single-symbol runs too.
        """
        timestamp = datetime(2025, 11, 6, 14, 30, 45, tzinfo=UTC)

        # Test with symbol_tag
        filename = generate_output_filename(
            direction=DirectionMode.BOTH,
            output_format=OutputFormat.TEXT,
            timestamp=timestamp,
            symbol_tag="eurusd",
        )

        # Should match: backtest_{direction}_{symbol}_{YYYYMMDD}_{HHMMSS}.txt
        pattern = r"^backtest_both_eurusd_\d{8}_\d{6}\.txt$"
        assert re.match(
            pattern, filename
        ), f"Filename '{filename}' does not match expected pattern"
        assert filename == "backtest_both_eurusd_20251106_143045.txt"

    def test_filename_directions(self):
        """Test filename generation for all direction modes."""
        timestamp = datetime(2025, 11, 6, 14, 30, 45, tzinfo=UTC)

        for direction in [DirectionMode.LONG, DirectionMode.SHORT, DirectionMode.BOTH]:
            filename = generate_output_filename(
                direction=direction,
                output_format=OutputFormat.TEXT,
                timestamp=timestamp,
                symbol_tag=None,
            )

            direction_str = direction.value.lower()
            assert direction_str in filename
            assert filename.startswith("backtest_")
            assert filename.endswith(".txt")

    def test_filename_output_formats(self):
        """Test filename generation for different output formats."""
        timestamp = datetime(2025, 11, 6, 14, 30, 45, tzinfo=UTC)

        # TEXT format
        txt_filename = generate_output_filename(
            direction=DirectionMode.LONG,
            output_format=OutputFormat.TEXT,
            timestamp=timestamp,
            symbol_tag=None,
        )
        assert txt_filename.endswith(".txt")

        # JSON format
        json_filename = generate_output_filename(
            direction=DirectionMode.LONG,
            output_format=OutputFormat.JSON,
            timestamp=timestamp,
            symbol_tag=None,
        )
        assert json_filename.endswith(".json")

    def test_multi_symbol_tag(self):
        """Test filename with 'multi' tag for multi-symbol runs."""
        timestamp = datetime(2025, 11, 6, 14, 30, 45, tzinfo=UTC)

        filename = generate_output_filename(
            direction=DirectionMode.BOTH,
            output_format=OutputFormat.TEXT,
            timestamp=timestamp,
            symbol_tag="multi",
        )

        assert "multi" in filename
        assert filename == "backtest_both_multi_20251106_143045.txt"
