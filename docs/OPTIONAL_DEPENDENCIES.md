# Optional Dependencies Guide

## Overview

Automagik-Omni supports multiple messaging channels. While WhatsApp support is included in the core dependencies, other channels like Discord require additional packages.

## Core Dependencies

The base installation includes all dependencies needed for:
- WhatsApp messaging
- Core API functionality
- Database operations
- Basic CLI commands

## Optional Channel Support

### Discord Support

Discord integration requires additional packages that are not installed by default to keep the core installation lightweight.

#### Installation

To enable Discord support, install the optional dependencies:

```bash
# Basic Discord support (text channels only)
pip install "automagik-omni[discord]"

# Discord with voice channel support
pip install "automagik-omni[discord-voice]"

# Discord with AI-powered voice features
pip install "automagik-omni[discord-voice-ai]"
```

#### Required Packages

The `discord` extra includes:
- `discord.py>=2.4.0` - Discord API wrapper
- `PyNaCl>=1.5.0` - Voice support library
- `aiohttp>=3.8.0` - Async HTTP client required by discord.py

#### Running Without Discord

The application will run normally without Discord dependencies. You'll see informational messages like:
```
Discord dependencies not installed. Discord support disabled.
```

This is expected behavior and the application will continue to work with WhatsApp and other configured channels.

## Installation Methods

### Development Installation

For development with all optional dependencies:

```bash
# Clone the repository
git clone https://github.com/yourusername/automagik-omni.git
cd automagik-omni

# Install with Discord support
pip install -e ".[discord]"

# Or install with all voice features
pip install -e ".[discord-voice-ai]"
```

### Production Installation

For production deployments, only install what you need:

```bash
# WhatsApp only (minimal installation)
pip install automagik-omni

# WhatsApp + Discord text
pip install "automagik-omni[discord]"

# Full feature set
pip install "automagik-omni[discord-voice-ai]"
```

## Troubleshooting

### ModuleNotFoundError: No module named 'aiohttp'

This error indicates Discord support is being used but the dependencies aren't installed. Solution:

```bash
pip install aiohttp discord.py PyNaCl
# Or
pip install "automagik-omni[discord]"
```

### Discord features not available

If Discord commands or features aren't working:

1. Check if Discord dependencies are installed:
   ```python
   python -c "import discord; print('Discord.py is installed')"
   ```

2. Install if missing:
   ```bash
   pip install "automagik-omni[discord]"
   ```

3. Restart the application

## Environment Detection

The application automatically detects available dependencies and enables/disables features accordingly:

- ✅ WhatsApp: Always available (core dependency)
- ⚠️ Discord: Available only if discord.py is installed
- ⚠️ Voice features: Available only if additional voice dependencies are installed

## Docker Deployments

For Docker deployments, specify the extras in your Dockerfile:

```dockerfile
# Minimal installation
RUN pip install automagik-omni

# With Discord support
RUN pip install "automagik-omni[discord]"
```

Or use environment-specific requirements files:

```dockerfile
# requirements-prod.txt for production (minimal)
# requirements-dev.txt for development (all features)
COPY requirements-${ENV}.txt .
RUN pip install -r requirements-${ENV}.txt
```