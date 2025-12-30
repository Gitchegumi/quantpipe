"""
U.S. market holiday detection for calendar generation.

This module provides functions to detect U.S. market holidays (NYSE calendar)
including fixed holidays, floating holidays, and observed rules.
"""

from datetime import date, timedelta
from functools import lru_cache


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """
    Find the nth occurrence of a weekday in a month.

    Args:
        year: Calendar year.
        month: Calendar month (1-12).
        weekday: Target weekday (0=Monday, 6=Sunday).
        n: Which occurrence (1=first, 2=second, etc.).

    Returns:
        Date of the nth weekday in the month.
    """
    first_day = date(year, month, 1)
    # Days until first occurrence of target weekday
    days_until = (weekday - first_day.weekday()) % 7
    first_occurrence = first_day + timedelta(days=days_until)
    # Add (n-1) weeks
    return first_occurrence + timedelta(weeks=n - 1)


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """
    Find the last occurrence of a weekday in a month.

    Args:
        year: Calendar year.
        month: Calendar month (1-12).
        weekday: Target weekday (0=Monday, 6=Sunday).

    Returns:
        Date of the last weekday in the month.
    """
    # Start from last day of month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # Walk backwards to find target weekday
    days_back = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=days_back)


def _easter_sunday(year: int) -> date:
    """
    Calculate Easter Sunday using the Anonymous Gregorian algorithm.

    Args:
        year: Calendar year.

    Returns:
        Date of Easter Sunday.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed_date(holiday: date) -> date:
    """
    Apply weekend observation rules.

    - Saturday holiday → observed Friday
    - Sunday holiday → observed Monday

    Args:
        holiday: Original holiday date.

    Returns:
        Observed date (may be same as original).
    """
    if holiday.weekday() == 5:  # Saturday
        return holiday - timedelta(days=1)  # Friday
    elif holiday.weekday() == 6:  # Sunday
        return holiday + timedelta(days=1)  # Monday
    return holiday


@lru_cache(maxsize=50)
def get_us_holidays_for_year(year: int) -> tuple[date, ...]:
    """
    Generate all U.S. market holidays for a given year.

    Returns major NYSE holidays in chronological order.

    Args:
        year: Calendar year.

    Returns:
        Tuple of holiday dates (sorted).

    Example:
        >>> holidays = get_us_holidays_for_year(2023)
        >>> len(holidays) >= 10
        True
    """
    holidays: list[date] = []

    # New Year's Day (January 1, observed)
    new_years = _observed_date(date(year, 1, 1))
    holidays.append(new_years)

    # MLK Day (3rd Monday of January)
    mlk_day = _nth_weekday_of_month(year, 1, 0, 3)  # Monday=0
    holidays.append(mlk_day)

    # Presidents Day (3rd Monday of February)
    presidents_day = _nth_weekday_of_month(year, 2, 0, 3)
    holidays.append(presidents_day)

    # Good Friday (Friday before Easter Sunday)
    easter = _easter_sunday(year)
    good_friday = easter - timedelta(days=2)
    holidays.append(good_friday)

    # Memorial Day (last Monday of May)
    memorial_day = _last_weekday_of_month(year, 5, 0)
    holidays.append(memorial_day)

    # Juneteenth (June 19, observed) - since 2021
    if year >= 2021:
        juneteenth = _observed_date(date(year, 6, 19))
        holidays.append(juneteenth)

    # Independence Day (July 4, observed)
    independence_day = _observed_date(date(year, 7, 4))
    holidays.append(independence_day)

    # Labor Day (1st Monday of September)
    labor_day = _nth_weekday_of_month(year, 9, 0, 1)
    holidays.append(labor_day)

    # Thanksgiving (4th Thursday of November)
    thanksgiving = _nth_weekday_of_month(year, 11, 3, 4)  # Thursday=3
    holidays.append(thanksgiving)

    # Christmas (December 25, observed)
    christmas = _observed_date(date(year, 12, 25))
    holidays.append(christmas)

    return tuple(sorted(holidays))


def is_us_market_holiday(check_date: date) -> bool:
    """
    Check if a date is a U.S. market holiday.

    Args:
        check_date: Date to check.

    Returns:
        True if the date is a holiday, False otherwise.

    Example:
        >>> is_us_market_holiday(date(2023, 7, 4))
        True
        >>> is_us_market_holiday(date(2023, 3, 15))
        False
    """
    holidays = get_us_holidays_for_year(check_date.year)
    return check_date in holidays
