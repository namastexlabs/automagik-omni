"""
PyInstaller hook for ctypes
Suppresses warnings for platform-specific DLLs when cross-compiling
"""
import sys

# When building on Linux/Mac, exclude Windows-specific DLLs
if sys.platform != 'win32':
    excludedimports = [
        'ctypes.wintypes',
    ]

    # Note: The user32.dll warning cannot be fully suppressed as it comes from
    # runtime ctypes.util.find_library() calls in dependencies (discord.py, etc.)
    # This is expected and harmless when building on Linux for cross-platform use.
