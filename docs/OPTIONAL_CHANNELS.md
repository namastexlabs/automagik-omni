# Optional Channel Dependencies Pattern

This document describes how to make a channel (like Discord, Telegram, etc.) an optional dependency in automagik-omni.

## Architecture Overview

Omni Hub uses a **modular channel architecture** where channels can be installed independently:

```
Core Install (193MB):
  pip install automagik-omni

With Discord (additional ~42MB):
  pip install automagik-omni[discord]

With All Channels:
  pip install automagik-omni[all-channels]
```

## How to Make a Channel Optional

### Step 1: Define Optional Dependency in pyproject.toml

```toml
[project.optional-dependencies]
discord = ["discord.py>=2.0.0"]
discord-voice = ["discord.py[voice]>=2.0.0"]
telegram = ["python-telegram-bot>=20.0"]
all-channels = ["automagik-omni[discord,telegram]"]
```

### Step 2: Guard Imports with Early Exit Pattern

In the channel's main module (e.g., `bot_manager.py`):

```python
# Channel is an optional dependency - guard the import
try:
    import channel_lib
    CHANNEL_AVAILABLE = True
except ImportError:
    channel_lib = None
    CHANNEL_AVAILABLE = False
    # Early exit - raise ImportError to prevent class definitions
    # This is caught by src/channels/channelname/__init__.py
    raise ImportError("channel_lib not installed")

# Rest of the module (class definitions, etc.)
class ChannelBot(channel_lib.Bot):
    ...
```

**Why Early Exit?**
- Python executes class definitions at import time
- `class Foo(lib.Bar)` fails if `lib` is `None`
- Early exit prevents reaching class definitions
- The ImportError is caught by the parent `__init__.py`

### Step 3: Guard Channel Package __init__.py

In `src/channels/channelname/__init__.py`:

```python
"""Channel implementation."""
import logging

logger = logging.getLogger(__name__)

# Components - all optional, guarded by try-except
CHANNEL_COMPONENTS_AVAILABLE = False
ChannelHandler = None
ChannelManager = None

try:
    from .channel_handler import ChannelHandler
    from .manager import ChannelManager
    CHANNEL_COMPONENTS_AVAILABLE = True
    logger.info("Channel components loaded successfully")
except (ImportError, AttributeError) as e:
    logger.warning(f"Channel components not available: {e}. Install with: uv sync --extra channelname")

__all__ = [
    "CHANNEL_COMPONENTS_AVAILABLE",
    "ChannelHandler",
    "ChannelManager",
]
```

### Step 4: Register Handler Conditionally

In `src/channels/__init__.py`:

```python
# Register Channel handler (if dependencies installed)
try:
    import channel_lib
    from src.channels.channelname.channel_handler import ChannelHandler
    ChannelHandlerFactory.register_handler("channelname", ChannelHandler)
    logger.info("Channel handler registered")
except (ImportError, AttributeError):
    logger.info("Channel dependencies not installed. Install with: uv sync --extra channelname")
```

### Step 5: Add Tests for Graceful Degradation

Add tests in `tests/channels/test_optional_dependencies.py`:

```python
def test_channel_components_flag_exists(self):
    """Verify CHANNEL_COMPONENTS_AVAILABLE flag is properly set."""
    result = subprocess.run(
        [sys.executable, "-c",
         "from src.channels.channelname import CHANNEL_COMPONENTS_AVAILABLE; "
         "assert isinstance(CHANNEL_COMPONENTS_AVAILABLE, bool); "
         "print('SUCCESS')"],
        capture_output=True, text=True,
        cwd="/path/to/automagik-omni",
        timeout=30,
    )
    assert result.returncode == 0
    assert "SUCCESS" in result.stdout
```

## Key Patterns

### 1. Early Exit Pattern
```python
try:
    import lib
    AVAILABLE = True
except ImportError:
    lib = None
    AVAILABLE = False
    raise ImportError("lib not installed")  # Early exit!
```

### 2. Availability Flag Pattern
```python
CHANNEL_COMPONENTS_AVAILABLE = False  # Default
try:
    from .module import Component
    CHANNEL_COMPONENTS_AVAILABLE = True
except (ImportError, AttributeError):
    pass
```

### 3. String Type Hints Pattern
When type hints reference optional types:
```python
# Bad - fails when discord is None
def foo(client: discord.Client): ...

# Good - string annotation, evaluated lazily
def foo(client: "discord.Client"): ...
```

### 4. Conditional Class Definition Pattern
When you need a class that inherits from optional base:
```python
if AVAILABLE and BaseClass is not None:
    class MyClass(BaseClass):
        ...
else:
    MyClass = None
```

## Checklist for New Optional Channels

- [ ] Add to `pyproject.toml` optional-dependencies
- [ ] Add early exit pattern to main channel modules
- [ ] Create `__init__.py` with availability flag and guarded imports
- [ ] Register handler conditionally in `src/channels/__init__.py`
- [ ] Use string type hints for optional types
- [ ] Add graceful degradation tests
- [ ] Update install documentation
- [ ] Run `benchmarks/startup_time.py` to verify no performance regression

## Files Modified for Discord Example

1. `pyproject.toml` - Added `[project.optional-dependencies]`
2. `src/channels/discord/bot_manager.py` - Early exit pattern
3. `src/channels/discord/voice_manager.py` - Early exit pattern
4. `src/channels/discord/__init__.py` - Availability flag + guarded imports
5. `src/channels/__init__.py` - Conditional registration
6. `tests/channels/test_optional_dependencies.py` - Graceful degradation tests

## Performance Impact

Measured overhead: **~0.3ms** total for all guards (negligible)

Memory savings when channel unavailable: **~35MB** for Discord
