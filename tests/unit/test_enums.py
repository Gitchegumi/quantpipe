pytestmark = pytest.mark.unit
"""
Unit tests for directional backtesting enumerations.

Tests type-safe enums for direction modes and output formats.
"""

import pytest

from src.models.enums import DirectionMode, OutputFormat


class TestDirectionMode:
    """Test cases for DirectionMode enumeration."""

    def test_direction_mode_values(self):
        """Verify DirectionMode has exactly three valid values: LONG, SHORT, BOTH."""
        assert DirectionMode.LONG.value == "LONG"
        assert DirectionMode.SHORT.value == "SHORT"
        assert DirectionMode.BOTH.value == "BOTH"

    def test_direction_mode_string_comparison(self):
        """Verify DirectionMode supports string equality comparison."""
        assert DirectionMode.LONG == "LONG"
        assert DirectionMode.SHORT == "SHORT"
        assert DirectionMode.BOTH == "BOTH"

    def test_direction_mode_membership(self):
        """Verify DirectionMode can be used in membership tests."""
        valid_modes = list(DirectionMode)
        assert DirectionMode.LONG in valid_modes
        assert DirectionMode.SHORT in valid_modes
        assert DirectionMode.BOTH in valid_modes
        assert len(valid_modes) == 3

    def test_direction_mode_iteration(self):
        """Verify DirectionMode enumeration can be iterated."""
        modes = [mode.value for mode in DirectionMode]
        assert modes == ["LONG", "SHORT", "BOTH"]

    def test_direction_mode_from_string(self):
        """Verify DirectionMode can be constructed from string values."""
        assert DirectionMode("LONG") == DirectionMode.LONG
        assert DirectionMode("SHORT") == DirectionMode.SHORT
        assert DirectionMode("BOTH") == DirectionMode.BOTH

    def test_direction_mode_invalid_value(self):
        """Verify DirectionMode raises ValueError for invalid string."""
        with pytest.raises(ValueError, match="'INVALID' is not a valid DirectionMode"):
            DirectionMode("INVALID")


class TestOutputFormat:
    """Test cases for OutputFormat enumeration."""

    def test_output_format_values(self):
        """Verify OutputFormat has exactly two valid values: text, json."""
        assert OutputFormat.TEXT.value == "text"
        assert OutputFormat.JSON.value == "json"

    def test_output_format_string_comparison(self):
        """Verify OutputFormat supports string equality comparison."""
        assert OutputFormat.TEXT == "text"
        assert OutputFormat.JSON == "json"

    def test_output_format_membership(self):
        """Verify OutputFormat can be used in membership tests."""
        valid_formats = list(OutputFormat)
        assert OutputFormat.TEXT in valid_formats
        assert OutputFormat.JSON in valid_formats
        assert len(valid_formats) == 2

    def test_output_format_iteration(self):
        """Verify OutputFormat enumeration can be iterated."""
        formats = [fmt.value for fmt in OutputFormat]
        assert formats == ["text", "json"]

    def test_output_format_from_string(self):
        """Verify OutputFormat can be constructed from string values."""
        assert OutputFormat("text") == OutputFormat.TEXT
        assert OutputFormat("json") == OutputFormat.JSON

    def test_output_format_invalid_value(self):
        """Verify OutputFormat raises ValueError for invalid string."""
        with pytest.raises(ValueError, match="'xml' is not a valid OutputFormat"):
            OutputFormat("xml")
