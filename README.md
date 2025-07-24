# Automagik Omni

Multi-tenant omnichannel messaging hub with AI agent integration.

## Overview

This project implements an AI agent system that can integrate with various communication channels, starting with WhatsApp.

## Setup

1. Create a virtual environment: `python -m venv .venv`
2. Activate the virtual environment: `source .venv/bin/activate`
3. Install dependencies: `uv pip install -e .`

## Configuration

Copy the `.env.example` file (if available) to `.env` and fill in the required configuration values.

## Running the Application

```bash
automagik-omni start
```

Or using the legacy command:
```bash
omnihub start
```

Or using the legacy method:
```bash
python -m src.main
```

## CLI Commands

```bash
# Main commands
automagik-omni start              # Start the API server
automagik-omni status             # Show system status
automagik-omni health             # Health check

# Instance management
automagik-omni instance list      # List all instances
automagik-omni instance add       # Add new instance
automagik-omni instance show      # Show instance details

# Telemetry management
automagik-omni telemetry enable   # Enable usage analytics
automagik-omni telemetry disable  # Disable usage analytics
```

## Telemetry

Automagik Omni collects anonymous usage analytics to help improve the product. This includes:
- CLI command usage patterns
- API endpoint performance metrics
- System information (OS, Python version)

**No personal data, message content, or credentials are collected.**

To disable telemetry:
```bash
automagik-omni telemetry disable
```

Or set environment variable:
```bash
export AUTOMAGIK_OMNI_DISABLE_TELEMETRY=true
```

## Testing

### Running Tests

```bash
# Run all tests
npm run test

# Run tests with coverage
npm run coverage

# Run specific test file
pytest tests/test_specific.py
```

### Test Database Configuration

By default, tests use an in-memory SQLite database for isolation. To test with PostgreSQL or a persistent database, set the `TEST_DATABASE_URL` environment variable:

```bash
# Test with PostgreSQL
export TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:15401/automagik_omni_test"
npm run test

# Test with persistent SQLite
export TEST_DATABASE_URL="sqlite:///./test_data/test.db"
npm run test
```

**Important**: The test database is completely wiped and recreated for each test function to ensure test isolation.

## Development

This project uses `uv` as the package manager. To add new dependencies:

```bash
uv add <package-name>
```

## Project Structure

- `src/` - Main source code directory
  - `agent/` - Agent implementation
  - `channels/` - Communication channel integrations
  - `db/` - Database models and repositories
- `tests/` - Test directory (to be implemented) 