# Omnichannel Agent

AI agent integration for OmniChannels.

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
omnihub start
```

Or using the legacy method:
```bash
python -m src.main
```

## CLI Commands

```bash
# Main commands
omnihub start              # Start the API server
omnihub status             # Show system status
omnihub health             # Health check

# Instance management
omnihub instance list      # List all instances
omnihub instance add       # Add new instance
omnihub instance show      # Show instance details

# Telemetry management
omnihub telemetry enable   # Enable usage analytics
omnihub telemetry disable  # Disable usage analytics
```

## Telemetry

Omni-Hub collects anonymous usage analytics to help improve the product. This includes:
- CLI command usage patterns
- API endpoint performance metrics
- System information (OS, Python version)

**No personal data, message content, or credentials are collected.**

To disable telemetry:
```bash
omnihub telemetry disable
```

Or set environment variable:
```bash
export OMNI_HUB_DISABLE_TELEMETRY=true
```

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