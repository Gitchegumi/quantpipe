"""
Unit tests for U.S. market holiday detection.

Tests validate holiday detection for NYSE trading calendar,
including fixed holidays, floating holidays, and observed rules.
"""

from datetime import date

import pytest

from src.risk.blackout.holidays import (
    is_us_market_holiday,
    get_us_holidays_for_year,
)


pytestmark = pytest.mark.unit


class TestFixedHolidays:
    """Test detection of fixed-date holidays."""

    def test_independence_day_detected(self):
        """July 4th should be detected as a holiday."""
        assert is_us_market_holiday(date(2023, 7, 4)) is True

    def test_christmas_detected(self):
        """December 25 should be detected as a holiday."""
        assert is_us_market_holiday(date(2023, 12, 25)) is True

    def test_new_years_day_detected(self):
        """January 1 should be detected as a holiday."""
        assert is_us_market_holiday(date(2023, 1, 2))  # Jan 1 is Sunday, observed Mon

    def test_juneteenth_detected(self):
        """June 19 should be detected as a holiday (since 2021)."""
        assert is_us_market_holiday(date(2023, 6, 19)) is True

    def test_juneteenth_not_before_2021(self):
        """June 19 should NOT be a holiday before 2021."""
        assert is_us_market_holiday(date(2020, 6, 19)) is False


class TestFloatingHolidays:
    """Test detection of floating holidays."""

    def test_mlk_day_third_monday_january(self):
        """MLK Day is 3rd Monday of January."""
        # 2023: Jan 16 is 3rd Monday
        assert is_us_market_holiday(date(2023, 1, 16)) is True

    def test_presidents_day_third_monday_february(self):
        """Presidents Day is 3rd Monday of February."""
        # 2023: Feb 20 is 3rd Monday
        assert is_us_market_holiday(date(2023, 2, 20)) is True

    def test_memorial_day_last_monday_may(self):
        """Memorial Day is last Monday of May."""
        # 2023: May 29 is last Monday
        assert is_us_market_holiday(date(2023, 5, 29)) is True

    def test_labor_day_first_monday_september(self):
        """Labor Day is 1st Monday of September."""
        # 2023: Sept 4 is 1st Monday
        assert is_us_market_holiday(date(2023, 9, 4)) is True

    def test_thanksgiving_fourth_thursday_november(self):
        """Thanksgiving is 4th Thursday of November."""
        # 2023: Nov 23 is 4th Thursday
        assert is_us_market_holiday(date(2023, 11, 23)) is True


class TestGoodFriday:
    """Test Good Friday detection (Friday before Easter)."""

    def test_good_friday_2023(self):
        """Good Friday 2023 is April 7."""
        assert is_us_market_holiday(date(2023, 4, 7)) is True

    def test_good_friday_2024(self):
        """Good Friday 2024 is March 29."""
        assert is_us_market_holiday(date(2024, 3, 29)) is True


class TestObservedRules:
    """Test weekend observation rules."""

    def test_july_4_saturday_observed_friday(self):
        """When July 4 is Saturday, observed on Friday."""
        # 2020: July 4 was Saturday, July 3 observed
        assert is_us_market_holiday(date(2020, 7, 3)) is True

    def test_july_4_sunday_observed_monday(self):
        """When July 4 is Sunday, observed on Monday."""
        # 2021: July 4 was Sunday, July 5 observed
        assert is_us_market_holiday(date(2021, 7, 5)) is True


class TestNonHolidays:
    """Test that regular trading days are not flagged."""

    def test_regular_monday(self):
        """A regular Monday should not be a holiday."""
        assert is_us_market_holiday(date(2023, 3, 6)) is False

    def test_regular_friday(self):
        """A regular Friday should not be a holiday."""
        assert is_us_market_holiday(date(2023, 3, 10)) is False


class TestGetHolidaysForYear:
    """Test annual holiday list generation."""

    def test_returns_all_major_holidays(self):
        """Should return at least 10 holidays per year."""
        holidays = get_us_holidays_for_year(2023)
        assert len(holidays) >= 10

    def test_holidays_are_sorted(self):
        """Holidays should be returned in chronological order."""
        holidays = get_us_holidays_for_year(2023)
        assert list(holidays) == sorted(holidays)

    def test_deterministic_output(self):
        """Same year should always produce same holidays."""
        holidays1 = get_us_holidays_for_year(2023)
        holidays2 = get_us_holidays_for_year(2023)
        assert holidays1 == holidays2
