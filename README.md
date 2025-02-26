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
python -m src.main
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