"""Tests for src/utils/instance_utils.py module."""
import pytest
from src.utils.instance_utils import normalize_instance_name, validate_instance_name


# Tests for normalize_instance_name()
class TestNormalizeInstanceName:
    """Test suite for normalize_instance_name function."""

    def test_normalize_empty_string(self):
        """Test normalization of empty string returns default instance."""
        assert normalize_instance_name("") == "default-instance"

    def test_normalize_spaces_to_hyphens(self):
        """Test that spaces are replaced with hyphens."""
        assert normalize_instance_name("my instance") == "my-instance"

    def test_normalize_multiple_spaces_to_single_hyphen(self):
        """Test that multiple spaces are replaced with single hyphen."""
        assert normalize_instance_name("my   instance") == "my-instance"

    def test_normalize_to_lowercase(self):
        """Test that names are converted to lowercase."""
        assert normalize_instance_name("MyInstance") == "myinstance"

    def test_normalize_removes_special_characters(self):
        """Test removal of special characters except hyphens and underscores."""
        assert normalize_instance_name("my@instance!") == "myinstance"

    def test_normalize_keeps_underscores(self):
        """Test that underscores are preserved."""
        assert normalize_instance_name("my_instance") == "my_instance"

    def test_normalize_removes_leading_hyphens(self):
        """Test removal of leading hyphens."""
        assert normalize_instance_name("-my-instance") == "my-instance"

    def test_normalize_removes_trailing_hyphens(self):
        """Test removal of trailing hyphens."""
        assert normalize_instance_name("my-instance-") == "my-instance"

    def test_normalize_consecutive_hyphens(self):
        """Test that consecutive hyphens are collapsed into single hyphen."""
        assert normalize_instance_name("my--instance") == "my-instance"

    def test_normalize_consecutive_underscores(self):
        """Test that consecutive underscores are collapsed into single hyphen."""
        assert normalize_instance_name("my__instance") == "my-instance"

    def test_normalize_mixed_consecutive_characters(self):
        """Test that mixed consecutive hyphens/underscores collapse correctly."""
        assert normalize_instance_name("my-_-instance") == "my-instance"

    def test_normalize_unicode_characters(self):
        """Test handling of unicode characters."""
        result = normalize_instance_name("instância")
        assert isinstance(result, str)
        assert result != "instância"  # Should be modified

    def test_normalize_very_short_name(self):
        """Test that very short names get padded."""
        result = normalize_instance_name("a")
        assert len(result) >= 2
        assert "instance" in result.lower()

    def test_normalize_length_limit(self):
        """Test that name is limited to 50 characters."""
        long_name = "a" * 100
        result = normalize_instance_name(long_name)
        assert len(result) <= 50

    def test_normalize_no_trailing_hyphen_after_truncation(self):
        """Test that truncated names don't end with hyphen."""
        # Create a name that will be truncated with hyphens at the end
        name = "valid-instance-" + "-" * 60
        result = normalize_instance_name(name)
        assert not result.endswith("-")

    def test_normalize_preserves_valid_name(self):
        """Test that a valid name remains unchanged."""
        assert normalize_instance_name("my-valid-instance") == "my-valid-instance"

    def test_normalize_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped."""
        assert normalize_instance_name("  my-instance  ") == "my-instance"

    def test_normalize_tabs_to_hyphens(self):
        """Test that tabs are replaced with hyphens."""
        result = normalize_instance_name("my\tinstance")
        assert "\t" not in result

    def test_normalize_newlines_to_hyphens(self):
        """Test that newlines are replaced with hyphens."""
        result = normalize_instance_name("my\ninstance")
        assert "\n" not in result


# Tests for validate_instance_name()
class TestValidateInstanceName:
    """Test suite for validate_instance_name function."""

    def test_validate_empty_string(self):
        """Test that empty string is rejected."""
        is_valid, error = validate_instance_name("")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_too_short(self):
        """Test that names shorter than 2 characters are rejected."""
        is_valid, error = validate_instance_name("a")
        assert is_valid is False
        assert "2 characters" in error.lower()

    def test_validate_too_long(self):
        """Test that names longer than 50 characters are rejected."""
        long_name = "a" * 51
        is_valid, error = validate_instance_name(long_name)
        assert is_valid is False
        assert "50 characters" in error.lower()

    def test_validate_valid_simple_name(self):
        """Test that valid simple names pass validation."""
        is_valid, error = validate_instance_name("my-instance")
        assert is_valid is True
        assert error == ""

    def test_validate_with_underscores(self):
        """Test that names with underscores are valid."""
        is_valid, error = validate_instance_name("my_instance")
        assert is_valid is True

    def test_validate_with_numbers(self):
        """Test that names with numbers are valid."""
        is_valid, error = validate_instance_name("instance123")
        assert is_valid is True

    def test_validate_rejects_special_characters(self):
        """Test that special characters are rejected."""
        is_valid, error = validate_instance_name("my@instance")
        assert is_valid is False
        assert "special characters" in error.lower() or "only contain" in error.lower()

    def test_validate_rejects_spaces(self):
        """Test that spaces are rejected."""
        is_valid, error = validate_instance_name("my instance")
        assert is_valid is False

    def test_validate_rejects_leading_hyphen(self):
        """Test that leading hyphens are rejected."""
        is_valid, error = validate_instance_name("-instance")
        assert is_valid is False
        assert "hyphen" in error.lower()

    def test_validate_rejects_trailing_hyphen(self):
        """Test that trailing hyphens are rejected."""
        is_valid, error = validate_instance_name("instance-")
        assert is_valid is False
        assert "hyphen" in error.lower()

    def test_validate_rejects_consecutive_hyphens(self):
        """Test that consecutive hyphens are rejected."""
        is_valid, error = validate_instance_name("my--instance")
        assert is_valid is False
        assert "consecutive" in error.lower()

    def test_validate_minimum_valid_length(self):
        """Test that exactly 2 character names are valid."""
        is_valid, error = validate_instance_name("ab")
        assert is_valid is True

    def test_validate_maximum_valid_length(self):
        """Test that exactly 50 character names are valid."""
        valid_name = "a" * 50
        is_valid, error = validate_instance_name(valid_name)
        assert is_valid is True

    def test_validate_case_sensitivity_uppercase(self):
        """Test validation of uppercase letters."""
        is_valid, error = validate_instance_name("MyInstance")
        assert is_valid is True  # Validation allows uppercase

    def test_validate_complex_valid_name(self):
        """Test validation of complex but valid names."""
        is_valid, error = validate_instance_name("my-valid_instance123")
        assert is_valid is True

    def test_validate_hyphen_in_middle(self):
        """Test that hyphens in the middle are valid."""
        is_valid, error = validate_instance_name("my-instance")
        assert is_valid is True

    def test_validate_underscore_in_middle(self):
        """Test that underscores in the middle are valid."""
        is_valid, error = validate_instance_name("my_instance")
        assert is_valid is True

    def test_validate_mixed_valid_characters(self):
        """Test validation with mixed alphanumeric, hyphens, and underscores."""
        is_valid, error = validate_instance_name("my-valid_123")
        assert is_valid is True
