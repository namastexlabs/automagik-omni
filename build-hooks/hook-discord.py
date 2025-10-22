# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller hook for discord.py

This hook prevents warnings about Windows DLLs (like user32.dll) when building
on non-Windows platforms. Discord.py uses ctypes for audio (Opus codec) but
doesn't require Windows-specific DLLs.

The "Library user32 required via ctypes not found" warning is harmless and occurs
because PyInstaller's ctypes scanner detects all ctypes usage but can't determine
platform-specific branches at analysis time.
"""

import sys

from PyInstaller.utils.hooks import collect_submodules

# Collect all discord submodules
hiddenimports = collect_submodules('discord')

# Exclude Windows-specific imports on non-Windows platforms
if sys.platform != 'win32':
    excludedimports = [
        'win32api',
        'win32con',
        'win32file',
        'win32pipe',
        'pywintypes',
        'winerror',
    ]
else:
    excludedimports = []
