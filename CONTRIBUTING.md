# Contributing to Automagik Omni

First off, thank you for considering contributing to Automagik Omni! It's people like you that make Automagik Omni the best omnipresent messaging hub for AI agents.

## 🎯 Philosophy

Automagik Omni is built by practitioners, for practitioners. We value:

- **Production readiness** over feature completeness
- **Developer experience** over implementation complexity
- **Universal compatibility** over platform lock-in
- **Clear communication** over assumed understanding

## 🚀 Ways to Contribute

### 1. Report Bugs 🐛

Found a bug? Help us squash it!

**Before submitting:**
- Check if the bug has already been reported in [Issues](https://github.com/namastexlabs/automagik-omni/issues)
- Verify the bug exists in the latest version
- Collect relevant information (OS, Python version, error messages, logs)

**When submitting:**
```markdown
**Bug Description**: Clear, concise description of the problem

**Steps to Reproduce**:
1. Step one
2. Step two
3. Expected vs actual behavior

**Environment**:
- OS: [e.g., Ubuntu 22.04]
- Python: [e.g., 3.12.1]
- Omni Version: [e.g., 1.2.3]
- Channel: [e.g., WhatsApp, Discord]

**Logs/Screenshots**:
[Attach relevant logs or screenshots]
```

### 2. Add New Channels ✨

Want to integrate a new messaging platform?

**Good channel proposals include:**
- **Platform details**: Which messaging service?
- **Use cases**: Why this channel matters
- **API availability**: Does the platform have a stable API?
- **Technical requirements**: Authentication, webhooks, etc.

### 3. Improve Documentation 📚

Documentation improvements are always welcome:
- Fix typos or clarify confusing sections
- Add examples for common use cases
- Create tutorials or integration guides
- Document edge cases and troubleshooting

### 4. Submit Code 💻

Ready to code? Awesome! Here's how to get started.

## 🛠️ Development Setup

### Prerequisites

- Python 3.12+ (3.11+ supported)
- PostgreSQL 16+ or SQLite (for development)
- Git
- Evolution API instance (for WhatsApp testing)
- Discord Bot Token (for Discord testing)

### Setup Steps

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/automagik-omni.git
cd automagik-omni

# 2. Install dependencies
make install

# 3. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 4. Run database migrations
make migrate

# 5. Run tests to verify setup
make test

# 6. Start development server
make dev
```

## 📋 Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/telegram-integration
# or
git checkout -b fix/whatsapp-timeout
```

**Branch naming conventions:**
- `feature/` - New channel integrations or features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or fixes

### 2. Make Your Changes

**Key principles:**
- Follow existing channel handler patterns
- Write or update tests for your changes
- Update documentation as needed
- Keep commits focused and atomic

**Code style:**
```bash
# Run linting
make lint

# Format code
make format

# Check all quality gates
make check
```

### 3. Test Your Changes

```bash
# Run all tests
make test

# Run specific test files
pytest tests/channels/test_whatsapp.py

# Run with coverage
make test-coverage

# Test your changes manually
make dev  # Start server and verify functionality
curl http://localhost:8000/health
```

### 4. Commit Your Changes

**Commit message format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature or channel
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(channels): add Telegram integration"
git commit -m "fix(whatsapp): handle webhook timeout gracefully"
git commit -m "docs(readme): update channel integration guide"
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/telegram-integration
```

Then create a Pull Request on GitHub.

## 📝 Pull Request Guidelines

### PR Title Format

Follow the same format as commit messages:
```
feat(channels): add Telegram channel support
```

### PR Description Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New channel integration
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Fixes #123
Related to #456

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing Done
- [ ] Added/updated unit tests
- [ ] Added/updated integration tests
- [ ] Manual testing with actual messaging platform
- [ ] All existing tests pass

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-reviewed my own code
- [ ] Commented code where necessary
- [ ] Updated documentation
- [ ] No sensitive data or credentials in code
- [ ] Environment variables documented in .env.example
- [ ] Channel configuration tested with real messages
```

### Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: Maintainers review your code
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, your PR will be merged

**What reviewers look for:**
- Code quality and pattern consistency
- Test coverage for changes
- Documentation updates
- Security considerations (credential handling)
- Performance implications (message throughput)

## 🏗️ Project Architecture

Understanding the codebase structure helps you contribute effectively:

```
automagik-omni/
├── automagik_omni/          # Main application
│   ├── channels/            # Channel handlers
│   │   ├── whatsapp/        # WhatsApp integration
│   │   ├── discord/         # Discord integration
│   │   └── base.py          # Base channel handler
│   ├── api/                 # FastAPI application
│   │   └── routes/          # API endpoints
│   ├── models/              # Database models
│   ├── services/            # Business logic
│   └── utils/               # Shared utilities
├── tests/                   # Test suite
│   ├── channels/            # Channel tests
│   ├── api/                 # API tests
│   └── integration/         # Integration tests
├── docs/                    # Documentation
└── migrations/              # Database migrations
```

### Key Patterns

**Channel Handler Pattern:**
```python
# automagik_omni/channels/my_channel/handler.py
class MyChannelHandler(BaseChannelHandler):
    """Handler for My Channel platform."""

    async def send_message(self, phone: str, message: str):
        """Send text message through My Channel."""
        # Implementation here
        pass

    async def receive_webhook(self, data: dict):
        """Process incoming webhook from My Channel."""
        # Implementation here
        pass
```

**Instance Configuration:**
```python
# Create instance via API
instance = {
    "name": "my-bot",
    "channel_type": "my_channel",
    "api_url": "https://api.mychannel.com",
    "api_key": "secret_key",
    "agent_url": "https://my-agent.com/chat"
}
```

**Testing Pattern:**
```python
# tests/channels/test_my_channel.py
@pytest.mark.asyncio
async def test_send_message():
    handler = MyChannelHandler()
    result = await handler.send_message("+123456789", "Test")
    assert result["status"] == "success"
```

## 🎓 Learning Resources

### Documentation
- [Main README](README.md) - Overview and quick start
- [API Documentation](docs/api.md) - API reference
- [Channel Integration Guide](docs/channels.md) - Adding new channels

### External Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - API framework
- [Evolution API](https://evolution-api.com/docs) - WhatsApp integration
- [Discord.py Documentation](https://discordpy.readthedocs.io/) - Discord bots

## ❓ Questions?

### Get Help

- **Discord**: [Join our community](https://discord.gg/xcW8c7fF3R)
- **GitHub Discussions**: [Ask questions](https://github.com/namastexlabs/automagik-omni/discussions)
- **Twitter**: [@namastexlabs](https://twitter.com/namastexlabs)

### Before Asking

1. Search existing issues and discussions
2. Check documentation (README, API docs, etc.)
3. Review the [DeepWiki docs](https://deepwiki.com/namastexlabs/automagik-omni)

## 📜 Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Our Standards

- **Be welcoming**: Help newcomers feel at home
- **Be respectful**: Disagree professionally
- **Be constructive**: Provide actionable feedback
- **Be patient**: Remember we're all learning

## 🎉 Recognition

Contributors who make significant impacts will be:
- Listed in our README acknowledgments
- Mentioned in release notes
- Invited to our contributors' Discord channel
- Given priority support for their own projects using Omni

## 🔒 Security

If you discover a security vulnerability, please email security@namastex.ai instead of opening a public issue.

## 📄 License

By contributing to Automagik Omni, you agree that your contributions will be licensed under the Apache License 2.0.

---

<p align="center">
  <strong>Thank you for contributing to Automagik Omni! 🎉</strong><br>
  Together, we're building the future of omnipresent AI messaging.
</p>

<p align="center">
  Made with ❤️ by <a href="https://namastex.ai">Namastex Labs</a> and amazing contributors like you
</p>