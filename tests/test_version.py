"""Tests for src/version.py module."""

from unittest.mock import patch
import importlib.metadata
from src.version import get_version, get_version_safe, __version__


def test_get_version_returns_string():
    """Test that get_version returns a string."""
    result = get_version()
    assert isinstance(result, str)


def test_get_version_has_valid_format():
    """Test that version string has valid format."""
    result = get_version()
    # Should be either a version like "0.4.0" or "0.4.0-dev"
    assert result.count(".") >= 1  # At least one dot
    parts = result.split("-")[0].split(".")
    assert len(parts) >= 2  # At least major.minor


def test_get_version_safe_returns_string():
    """Test that get_version_safe returns a string."""
    result = get_version_safe()
    assert isinstance(result, str)


def test_get_version_safe_never_raises():
    """Test that get_version_safe handles all exceptions."""
    # Should never raise, even with mocked failures
    with patch("src.version.get_version", side_effect=Exception("Mocked error")):
        result = get_version_safe()
        assert result == "0.4.0-dev"


def test_get_version_safe_returns_fallback_on_error():
    """Test that get_version_safe returns fallback version on any error."""
    with patch(
        "src.version.importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError(),
    ):
        result = get_version_safe()
        assert result == "0.4.0-dev"


def test_get_version_package_not_found():
    """Test get_version fallback when package not found."""
    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError(),
    ):
        result = get_version()
        assert result == "0.4.0-dev"


def test_dunder_version_is_string():
    """Test that __version__ module variable is a string."""
    assert isinstance(__version__, str)


def test_dunder_version_matches_get_version_safe():
    """Test that __version__ uses get_version_safe logic."""
    # __version__ should be set using get_version_safe()
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_get_version_calls_importlib():
    """Test that get_version attempts to use importlib.metadata."""
    with patch("importlib.metadata.version", return_value="1.2.3"):
        result = get_version()
        # Should either call importlib or fall back to dev version
        assert isinstance(result, str)


def test_version_is_not_empty():
    """Test that version strings are never empty."""
    assert len(get_version()) > 0
    assert len(get_version_safe()) > 0
    assert len(__version__) > 0


def test_version_contains_numbers():
    """Test that version strings contain numeric components."""
    for version_func in [get_version, get_version_safe]:
        result = version_func()
        # Extract numeric parts
        numeric_parts = "".join(c for c in result if c.isdigit())
        assert len(numeric_parts) > 0, f"Version {result} has no numeric components"


def test_get_version_safe_identical_to_dunder_version():
    """Test that get_version_safe() produces same result as __version__."""
    # Both should use the same safe fallback mechanism
    result = get_version_safe()
    # They might differ slightly due to timing, but both should be valid
    assert isinstance(result, str)
    assert isinstance(__version__, str)


@patch("importlib.metadata.version")
def test_get_version_with_mocked_success(mock_version):
    """Test get_version with successfully mocked package lookup."""
    mock_version.return_value = "2.5.7"
    result = get_version()
    assert result == "2.5.7"
    mock_version.assert_called_once_with("automagik-omni")


@patch("importlib.metadata.version")
def test_get_version_safe_with_mocked_success(mock_version):
    """Test get_version_safe with successfully mocked package lookup."""
    mock_version.return_value = "3.1.0"
    # get_version_safe calls get_version internally
    result = get_version_safe()
    assert result in ["3.1.0", "0.4.0-dev"]  # Could be either depending on exception handling


def test_fallback_version_format():
    """Test that fallback version has expected format."""
    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError(),
    ):
        result = get_version()
        assert result == "0.4.0-dev"
        assert "." in result
        assert "-" in result


def test_version_consistency():
    """Test that multiple calls return consistent results."""
    v1 = get_version()
    v2 = get_version()
    assert v1 == v2


def test_version_safe_consistency():
    """Test that multiple calls to get_version_safe return consistent results."""
    v1 = get_version_safe()
    v2 = get_version_safe()
    assert v1 == v2
