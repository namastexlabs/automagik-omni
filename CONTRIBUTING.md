# Contributing to Automagik Omni

Thank you for your interest in contributing to Automagik Omni! We're building the universal messaging hub for AI agents, and we'd love your help making it even better.

## 🚀 Quick Start

1. **Fork** the repository on GitHub
2. **Clone** your fork: `git clone https://github.com/YOUR_USERNAME/automagik-omni`
3. **Install** dependencies: `make install`
4. **Set up** environment: `cp .env.example .env`
5. **Run** migrations: `make migrate`
6. **Create** a branch: `git checkout -b feature/your-feature-name`
7. **Make** your changes
8. **Test**: `make test`
9. **Push** and create a Pull Request

## 📋 What We're Looking For

### New Channel Integrations
- **Messaging platforms**: Slack, Telegram, Instagram, etc.
- **Enterprise channels**: Microsoft Teams, LinkedIn Messages
- **Regional platforms**: WeChat, Line, Viber
- **Documentation**: Clear setup guides for each channel

### Core Features
- **Access control**: Whitelist/blacklist systems
- **Message routing**: Intelligent routing and filtering
- **Analytics**: Enhanced tracing and insights
- **Performance**: Optimization and scalability improvements

### Developer Experience
- **Better errors**: Clear, actionable error messages
- **More examples**: Sample integrations and use cases
- **CLI improvements**: Enhanced command-line tools
- **Documentation**: Tutorials, guides, and API references

## 🛠️ Development Process

### 1. Setting Up

```bash
# Clone and install
git clone https://github.com/namastexlabs/automagik-omni
cd automagik-omni

# Install with UV (fast Python package manager)
make install

# Set up environment
cp .env.example .env
# Edit .env with your test credentials

# Run migrations
make migrate

# Start development server
make dev
```

### 2. Making Changes

```bash
# Create feature branch from main
git checkout -b feature/your-feature-name

# Make your changes
# Edit files...

# Test locally
make test
make lint

# Run specific tests
pytest tests/test_your_feature.py -v
```

### 3. Testing

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=automagik_omni tests/

# Test specific module
pytest tests/services/test_message_handler.py -v

# Check code quality
make lint
make format
```

### 4. Submitting

```bash
# Commit with conventional commits
git add .
git commit -m "feat: add Telegram integration"

# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
```

## 📝 Pull Request Guidelines

### PR Title Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: Add Slack channel integration`
- `fix: Handle rate limiting in WhatsApp API`
- `docs: Update installation guide`
- `refactor: Simplify message routing logic`
- `test: Add integration tests for Discord`
- `chore: Update dependencies`

### PR Description Template

```markdown
## Description
Brief description of what this PR does

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
How to test these changes:
1. Step 1
2. Step 2
3. Expected result

## Breaking Changes
List any breaking changes (if applicable)

## Screenshots
Add screenshots for UI changes (if applicable)
```

### PR Checklist

Before submitting, ensure:

- [ ] Tests pass (`make test`)
- [ ] Code is formatted (`make format`)
- [ ] Code passes linting (`make lint`)
- [ ] Documentation updated (if needed)
- [ ] Tests added for new features
- [ ] PR title follows conventional commits
- [ ] No sensitive credentials in code
- [ ] Environment variables added to `.env.example`

## 🧪 Testing Guidelines

### Unit Tests

```python
import pytest
from automagik_omni.services.message_handler import MessageHandler

@pytest.mark.asyncio
async def test_message_routing():
    """Test message routing to correct agent."""
    handler = MessageHandler()

    # Arrange
    message = {"text": "Hello", "from": "+1234567890"}

    # Act
    result = await handler.route_message(message)

    # Assert
    assert result.status == "success"
    assert result.agent_id is not None
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_whatsapp_flow():
    """Test complete WhatsApp message flow."""
    # Test with real Evolution API (requires test instance)
    async with TestClient() as client:
        response = await client.post(
            "/api/v1/instances/test-bot/send-text",
            json={"phone": "+1234567890", "message": "Test"}
        )
        assert response.status_code == 200
```

### Testing Best Practices

1. **Mock external services**: Use `pytest-mock` for API calls
2. **Use fixtures**: Share test setup with `conftest.py`
3. **Test edge cases**: Null values, empty strings, rate limits
4. **Async tests**: Mark with `@pytest.mark.asyncio`
5. **Database tests**: Use test database or in-memory SQLite

## 📚 Documentation

When contributing, update relevant documentation:

### README.md
- Add new features to feature list
- Update installation steps if changed
- Add examples for new functionality

### API Documentation
- Document new endpoints
- Add request/response examples
- List query parameters and headers

### Code Documentation
```python
async def send_message(
    instance_name: str,
    phone: str,
    message: str
) -> MessageResult:
    """Send text message through instance.

    Args:
        instance_name: Name of the messaging instance
        phone: Recipient phone number with country code
        message: Text message to send

    Returns:
        MessageResult with message ID and status

    Raises:
        InstanceNotFoundError: If instance doesn't exist
        ValidationError: If phone number is invalid

    Example:
        >>> result = await send_message("my-bot", "+1234567890", "Hello!")
        >>> print(result.message_id)
        "msg_abc123"
    """
```

## 🏗️ Architecture Guidelines

### Project Structure

```
automagik_omni/
├── api/              # FastAPI routes and endpoints
├── services/         # Business logic
├── models/           # Database models
├── handlers/         # Channel-specific handlers
├── mcp/              # MCP server implementation
└── utils/            # Shared utilities

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── conftest.py       # Shared fixtures
```

### Code Style

- **Python 3.12+**: Use modern Python features
- **Type hints**: Always use type annotations
- **Async/await**: Prefer async for I/O operations
- **Pydantic**: Use for data validation
- **SQLAlchemy**: Use for database operations
- **FastAPI**: Follow FastAPI best practices

### Naming Conventions

```python
# Classes: PascalCase
class MessageHandler:
    pass

# Functions/methods: snake_case
async def send_message():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3

# Private: prefix with underscore
def _internal_helper():
    pass
```

## 🔒 Security Guidelines

### Sensitive Data

- **Never commit** API keys, tokens, or credentials
- **Use** environment variables for all secrets
- **Add** new secrets to `.env.example` (without values)
- **Validate** all user inputs
- **Sanitize** error messages (no credential leaks)

### API Security

```python
# Good: Use environment variables
api_key = os.getenv("EVOLUTION_API_KEY")

# Bad: Hardcoded credentials
api_key = "abc123xyz"  # NEVER DO THIS!
```

## 🌍 Channel Integration Guidelines

### Adding a New Channel

1. **Create handler**: `automagik_omni/handlers/your_channel.py`
2. **Implement interface**: Follow `BaseChannelHandler`
3. **Add config**: Environment variables for credentials
4. **Add tests**: Unit and integration tests
5. **Document**: Setup guide and examples

### Channel Handler Template

```python
from automagik_omni.handlers.base import BaseChannelHandler

class YourChannelHandler(BaseChannelHandler):
    """Handler for Your Channel integration."""

    async def send_text(self, recipient: str, message: str) -> dict:
        """Send text message."""
        pass

    async def send_media(self, recipient: str, media_url: str) -> dict:
        """Send media message."""
        pass

    async def get_status(self) -> dict:
        """Get connection status."""
        pass
```

## 🤝 Code of Conduct

We are committed to providing a welcoming and inclusive experience:

- **Be respectful**: Treat everyone with respect and kindness
- **Be inclusive**: Welcome newcomers and diverse perspectives
- **Be constructive**: Focus on helpful feedback
- **Be professional**: Keep interactions professional
- **Assume good faith**: Presume positive intentions

## 💬 Getting Help

### Community

- **Discord**: [Join our server](https://discord.gg/xcW8c7fF3R)
- **GitHub Issues**: Search existing issues or create new ones
- **GitHub Discussions**: Ask questions and share ideas

### Resources

- **Documentation**: [DeepWiki Docs](https://deepwiki.com/namastexlabs/automagik-omni)
- **API Reference**: See `/docs` endpoint when running locally
- **Examples**: Check `examples/` directory

## 🎯 Current Priorities

We're especially interested in contributions for:

1. **Slack Integration** (Q4 2025 priority)
2. **Access Control** (Whitelist/blacklist)
3. **WhatsApp Business API** (Flows support)
4. **Performance Optimization** (Scalability)
5. **Documentation** (Tutorials and guides)
6. **Test Coverage** (Expand test suite)

## 🏆 Recognition

Contributors are valued and recognized:

- Listed in our README acknowledgments
- Mentioned in release notes
- Invited to contributor Discord channel
- Priority support for future contributions

## 📜 License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

---

**Thank you for contributing to Automagik Omni!** 🌐

Every contribution, no matter how small, helps us build the universal messaging hub for AI agents.