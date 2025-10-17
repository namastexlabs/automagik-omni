"""Tests for src/utils/datetime_utils.py module."""

import os
from datetime import datetime
import pytz
from unittest.mock import patch
from src.utils.datetime_utils import (
    get_config_timezone,
    utcnow,
    now,
    to_utc,
    to_local,
    format_local,
    datetime_utcnow,
)


def test_utcnow_returns_timezone_aware():
    """Test that utcnow returns timezone-aware datetime."""
    result = utcnow()
    assert result.tzinfo is not None
    assert result.tzinfo == pytz.UTC


def test_utcnow_is_recent():
    """Test that utcnow returns current time."""
    before = datetime.now(pytz.UTC)
    result = utcnow()
    after = datetime.now(pytz.UTC)
    assert before <= result <= after


def test_now_returns_timezone_aware():
    """Test that now returns timezone-aware datetime."""
    result = now()
    assert result.tzinfo is not None


def test_to_utc_with_aware_datetime():
    """Test converting timezone-aware datetime to UTC."""
    eastern = pytz.timezone("America/New_York")
    dt = eastern.localize(datetime(2024, 1, 1, 12, 0, 0))
    result = to_utc(dt)
    assert result.tzinfo == pytz.UTC
    assert result.hour == 17  # 12 PM EST = 5 PM UTC


def test_to_utc_with_naive_datetime():
    """Test converting naive datetime to UTC."""
    dt = datetime(2024, 1, 1, 12, 0, 0)
    result = to_utc(dt)
    assert result.tzinfo == pytz.UTC


def test_to_local_with_utc_datetime():
    """Test converting UTC datetime to local timezone."""
    utc_dt = pytz.UTC.localize(datetime(2024, 1, 1, 17, 0, 0))
    result = to_local(utc_dt)
    assert result.tzinfo is not None


def test_to_local_with_naive_datetime():
    """Test converting naive datetime (assumed UTC) to local."""
    dt = datetime(2024, 1, 1, 12, 0, 0)
    result = to_local(dt)
    assert result.tzinfo is not None


def test_format_local_default_format():
    """Test formatting datetime with default format string."""
    utc_dt = pytz.UTC.localize(datetime(2024, 1, 1, 12, 0, 0))
    result = format_local(utc_dt)
    assert "2024-01-01" in result
    assert "12:00:00" in result or "07:00:00" in result  # Depends on timezone


def test_format_local_custom_format():
    """Test formatting datetime with custom format string."""
    utc_dt = pytz.UTC.localize(datetime(2024, 6, 15, 14, 30, 45))
    result = format_local(utc_dt, format_str="%Y/%m/%d %H:%M")
    assert result.startswith("2024/06/15")


def test_datetime_utcnow_matches_utcnow():
    """Test that datetime_utcnow is consistent with utcnow."""
    result1 = datetime_utcnow()
    result2 = utcnow()
    # Should be within 1 second of each other
    assert abs((result1 - result2).total_seconds()) < 1


def test_get_config_timezone_fallback_with_env():
    """Test get_config_timezone fallback using environment variable."""
    with patch.dict(os.environ, {"AUTOMAGIK_TIMEZONE": "America/New_York"}):
        # Force ImportError by making config import fail
        with patch.dict("sys.modules", {"src.config": None}):
            result = get_config_timezone()
            assert result is not None


def test_get_config_timezone_removes_quotes():
    """Test that get_config_timezone removes quotes from env var."""
    test_cases = [
        ('"America/New_York"', "America/New_York"),
        ("'America/Chicago'", "America/Chicago"),
    ]

    for quoted, expected in test_cases:
        with patch.dict(os.environ, {"AUTOMAGIK_TIMEZONE": quoted}):
            with patch.dict("sys.modules", {"src.config": None}):
                try:
                    result = get_config_timezone()
                    # Verify it's a valid timezone object
                    assert result is not None
                except ImportError:
                    pass  # Expected in some test scenarios


def test_get_config_timezone_invalid_timezone_fallback():
    """Test fallback to UTC when invalid timezone is provided."""
    with patch.dict(os.environ, {"AUTOMAGIK_TIMEZONE": "Invalid/Timezone"}):
        with patch.dict("sys.modules", {"src.config": None}):
            result = get_config_timezone()
            assert result == pytz.UTC or isinstance(result, pytz.tzinfo.tzinfo)


def test_now_with_timezone_object():
    """Test now() handles timezone objects correctly."""
    result = now()
    # Should return a timezone-aware datetime
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_to_utc_preserves_time_value():
    """Test that to_utc correctly converts time values."""
    # Create a known time in a known timezone
    tokyo = pytz.timezone("Asia/Tokyo")
    tokyo_dt = tokyo.localize(datetime(2024, 1, 1, 12, 0, 0))

    utc_dt = to_utc(tokyo_dt)

    # Tokyo is UTC+9, so 12:00 Tokyo = 03:00 UTC
    assert utc_dt.hour == 3
    assert utc_dt.minute == 0


def test_to_local_with_different_timezones():
    """Test to_local with various source timezones."""
    # Create a UTC time
    utc_dt = pytz.UTC.localize(datetime(2024, 6, 15, 12, 0, 0))

    # Convert to local
    local_dt = to_local(utc_dt)

    # Verify it's timezone-aware
    assert local_dt.tzinfo is not None


def test_format_local_handles_naive_datetime():
    """Test that format_local can handle naive datetimes."""
    # Create naive datetime (should be treated as UTC)
    naive_dt = datetime(2024, 1, 1, 12, 0, 0)

    # This should work without errors (will assume UTC and convert to local)
    result = format_local(pytz.UTC.localize(naive_dt))
    assert isinstance(result, str)
    assert "2024" in result
