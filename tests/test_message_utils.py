"""Tests for src/channels/message_utils.py module."""

from src.channels.message_utils import extract_response_text


def test_extract_response_text_from_string():
    """Test extracting text from a plain string."""
    response = "This is a simple message"
    assert extract_response_text(response) == "This is a simple message"


def test_extract_response_text_from_dict_message_field():
    """Test extracting text from dict with 'message' field."""
    response = {"message": "Hello from message field"}
    assert extract_response_text(response) == "Hello from message field"


def test_extract_response_text_from_dict_text_field():
    """Test extracting text from dict with 'text' field."""
    response = {"text": "Hello from text field"}
    assert extract_response_text(response) == "Hello from text field"


def test_extract_response_text_from_dict_content_field():
    """Test extracting text from dict with 'content' field."""
    response = {"content": "Hello from content field"}
    assert extract_response_text(response) == "Hello from content field"


def test_extract_response_text_from_dict_response_field():
    """Test extracting text from dict with 'response' field."""
    response = {"response": "Hello from response field"}
    assert extract_response_text(response) == "Hello from response field"


def test_extract_response_text_nested_data():
    """Test extracting text from nested 'data' field."""
    response = {"data": {"message": "Hello from nested data"}}
    assert extract_response_text(response) == "Hello from nested data"


def test_extract_response_text_deeply_nested():
    """Test extracting text from deeply nested structure."""
    response = {"data": {"data": {"text": "Deeply nested message"}}}
    assert extract_response_text(response) == "Deeply nested message"


def test_extract_response_text_empty_fields():
    """Test handling of dict with empty fields."""
    response = {"message": "", "text": "", "content": "Actual content"}
    assert extract_response_text(response) == "Actual content"


def test_extract_response_text_none_values():
    """Test handling of None values in fields."""
    response = {"message": None, "text": "Valid text"}
    assert extract_response_text(response) == "Valid text"


def test_extract_response_text_no_known_fields():
    """Test fallback to string conversion when no known fields exist."""
    response = {"unknown_field": "value", "another": 123}
    result = extract_response_text(response)
    assert isinstance(result, str)
    assert "unknown_field" in result


def test_extract_response_text_integer():
    """Test extraction from integer type."""
    response = 42
    assert extract_response_text(response) == "42"


def test_extract_response_text_list():
    """Test extraction from list type."""
    response = ["item1", "item2"]
    result = extract_response_text(response)
    assert isinstance(result, str)
    assert "item1" in result


def test_extract_response_text_boolean():
    """Test extraction from boolean type."""
    assert extract_response_text(True) == "True"
    assert extract_response_text(False) == "False"


def test_extract_response_text_field_priority():
    """Test that field priority is respected (message > text > content > response)."""
    # 'message' field should take priority
    response = {"message": "from message", "text": "from text", "content": "from content", "response": "from response"}
    assert extract_response_text(response) == "from message"


def test_extract_response_text_nested_priority():
    """Test nested extraction when top-level has no valid fields."""
    response = {"status": "ok", "data": {"content": "nested content"}}
    assert extract_response_text(response) == "nested content"


def test_extract_response_text_empty_string():
    """Test handling of empty string input."""
    assert extract_response_text("") == ""


def test_extract_response_text_whitespace_string():
    """Test handling of whitespace-only string."""
    assert extract_response_text("   ") == "   "


def test_extract_response_text_numeric_string():
    """Test handling of numeric string values."""
    response = {"message": "123"}
    assert extract_response_text(response) == "123"
