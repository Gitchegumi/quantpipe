"""Unit tests for timeframe parsing and validation.

Tests cover:
- Valid timeframe formats: 1m, 5m, 15m, 1h, 2h, 4h, 8h, 1d (FR-012)
- Arbitrary integer timeframes: 7m, 13m, 90m, 120m (FR-013)
- Invalid formats: 0m, -5m, 1.5h, 90s, abc, empty (FR-004)
- Conversion correctness: 2h -> 120 minutes, 1d -> 1440 minutes
"""

import pytest

from src.data_io.timeframe import (
    Timeframe,
    parse_timeframe,
    validate_timeframe,
    format_timeframe,
)


class TestTimeframeDataclass:
    """Tests for the Timeframe dataclass."""

    def test_timeframe_creation(self):
        """Test basic Timeframe creation."""
        tf = Timeframe(period_minutes=15, original_input="15m")
        assert tf.period_minutes == 15
        assert tf.original_input == "15m"
        assert tf.is_valid is True

    def test_timeframe_invalid_flag(self):
        """Test Timeframe with is_valid=False."""
        tf = Timeframe(period_minutes=0, original_input="invalid", is_valid=False)
        assert tf.is_valid is False


class TestParseTimeframe:
    """Tests for parse_timeframe function."""

    @pytest.mark.parametrize(
        "tf_str,expected_minutes",
        [
            # Standard timeframes (FR-012)
            ("1m", 1),
            ("5m", 5),
            ("15m", 15),
            ("30m", 30),
            ("1h", 60),
            ("2h", 120),
            ("4h", 240),
            ("8h", 480),
            ("1d", 1440),
            # Arbitrary integers (FR-013)
            ("7m", 7),
            ("13m", 13),
            ("90m", 90),
            ("120m", 120),
            # Uppercase variants
            ("15M", 15),
            ("1H", 60),
            ("1D", 1440),
        ],
    )
    def test_valid_timeframes(self, tf_str: str, expected_minutes: int):
        """Test parsing of valid timeframe strings."""
        tf = parse_timeframe(tf_str)
        assert tf.period_minutes == expected_minutes
        assert tf.is_valid is True

    @pytest.mark.parametrize(
        "invalid_tf",
        [
            "",  # Empty
            "0m",  # Zero value
            "-5m",  # Negative
            "1.5h",  # Decimal
            "90s",  # Seconds not supported
            "abc",  # Non-numeric
            "m",  # Missing value
            "15",  # Missing unit
            "15x",  # Invalid unit
            None,  # None type
        ],
    )
    def test_invalid_timeframes(self, invalid_tf):
        """Test that invalid timeframe formats raise ValueError."""
        with pytest.raises(ValueError):
            parse_timeframe(invalid_tf)

    def test_whitespace_handling(self):
        """Test that whitespace is trimmed from input."""
        tf = parse_timeframe("  15m  ")
        assert tf.period_minutes == 15
        assert tf.original_input == "15m"


class TestValidateTimeframe:
    """Tests for validate_timeframe function."""

    def test_valid_timeframe_passes(self):
        """Test that valid timeframe passes validation."""
        tf = Timeframe(period_minutes=15, original_input="15m", is_valid=True)
        validate_timeframe(tf)  # Should not raise

    def test_invalid_flag_raises(self):
        """Test that is_valid=False raises ValueError."""
        tf = Timeframe(period_minutes=15, original_input="invalid", is_valid=False)
        with pytest.raises(ValueError):
            validate_timeframe(tf)

    def test_zero_minutes_raises(self):
        """Test that zero period_minutes raises ValueError."""
        tf = Timeframe(period_minutes=0, original_input="0m", is_valid=True)
        with pytest.raises(ValueError):
            validate_timeframe(tf)


class TestFormatTimeframe:
    """Tests for format_timeframe function."""

    @pytest.mark.parametrize(
        "minutes,expected",
        [
            (1, "1m"),
            (15, "15m"),
            (30, "30m"),
            (60, "1h"),
            (120, "2h"),
            (240, "4h"),
            (1440, "1d"),
            (2880, "2d"),
            # Non-divisible by 60 stay as minutes
            (7, "7m"),
            (90, "90m"),
        ],
    )
    def test_format_timeframe(self, minutes: int, expected: str):
        """Test formatting minutes to human-readable timeframe string."""
        assert format_timeframe(minutes) == expected
