# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Automagik Omni Backend
Bundles the Python backend into a single executable

Build with: pyinstaller automagik-omni-backend.spec

CROSS-PLATFORM BUILD NOTES:
---------------------------
When building on Linux/WSL, you may see warnings like:
  "WARNING: Library user32 required via ctypes not found"

This is expected and harmless. The warning occurs because:
1. discord.py uses ctypes to load the Opus audio codec library
2. PyInstaller's static analysis scans all ctypes calls during build
3. It cannot determine platform-specific code paths at analysis time
4. Some dependencies may conditionally use Windows DLLs if available

The built executable will work correctly on the target platform.
Custom hooks in build-hooks/ suppress unnecessary platform-specific imports.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Project root directory
project_root = os.path.abspath('.')

# Platform detection for cross-platform builds
is_windows = sys.platform == 'win32'
is_linux = sys.platform.startswith('linux')
is_mac = sys.platform == 'darwin'

# Collect all submodules for key dependencies that use dynamic imports
hiddenimports = []

# Core FastAPI/Uvicorn dependencies
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('uvicorn.lifespan')
hiddenimports += collect_submodules('uvicorn.lifespan.on')
hiddenimports += collect_submodules('uvicorn.protocols')
hiddenimports += collect_submodules('uvicorn.protocols.http')
hiddenimports += collect_submodules('uvicorn.protocols.websockets')
hiddenimports += collect_submodules('uvicorn.loops')
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('starlette')
hiddenimports += collect_submodules('starlette.middleware')

# Pydantic (extensive dynamic imports)
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic.deprecated')
hiddenimports += collect_submodules('pydantic.json_schema')
hiddenimports += collect_submodules('pydantic_core')

# SQLAlchemy (database engine and dialects)
hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += collect_submodules('sqlalchemy.dialects')
hiddenimports += collect_submodules('sqlalchemy.dialects.postgresql')
hiddenimports += collect_submodules('sqlalchemy.dialects.sqlite')
hiddenimports += collect_submodules('sqlalchemy.engine')
hiddenimports += collect_submodules('sqlalchemy.pool')
hiddenimports += collect_submodules('alembic')
hiddenimports += ['psycopg2', 'psycopg2._psycopg']

# Typer/Rich for CLI
hiddenimports += collect_submodules('typer')
hiddenimports += collect_submodules('rich')
hiddenimports += collect_submodules('click')

# HTTP clients and async
hiddenimports += collect_submodules('httpx')
hiddenimports += collect_submodules('requests')
hiddenimports += collect_submodules('aiohttp')

# Discord.py (optional but common)
try:
    hiddenimports += collect_submodules('discord')
    hiddenimports += collect_submodules('discord.ext')
    hiddenimports += collect_submodules('discord.ext.commands')
except ImportError:
    pass  # Discord not installed, skip

# AWS SDK (boto3)
hiddenimports += collect_submodules('boto3')
hiddenimports += collect_submodules('botocore')

# Other dependencies
hiddenimports += [
    'pika',
    'dotenv',
    'pytz',
]

# Collect binary dependencies and data files for key packages
datas = []
binaries = []

# Collect pydantic data files
pydantic_datas, pydantic_binaries, _ = collect_all('pydantic')
datas += pydantic_datas
binaries += pydantic_binaries

# Collect pydantic_core data files
pydantic_core_datas, pydantic_core_binaries, _ = collect_all('pydantic_core')
datas += pydantic_core_datas
binaries += pydantic_core_binaries

# Collect sqlalchemy data files
sqlalchemy_datas, sqlalchemy_binaries, _ = collect_all('sqlalchemy')
datas += sqlalchemy_datas
binaries += sqlalchemy_binaries

# Add project-specific data files
datas += [
    ('src', 'src'),                           # All Python source code
    ('alembic', 'alembic'),                   # Database migrations
    ('alembic.ini', '.'),                     # Alembic config
    ('.env.example', '.'),                    # Example environment file
]

# Analysis configuration
a = Analysis(
    ['src/cli/main.py'],                      # Main entry point
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[os.path.join(project_root, 'build-hooks')],  # Custom hooks to suppress warnings
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'black',
        'mypy',
        'ruff',
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'alembic.testing',
        # SQLAlchemy optional drivers (not needed)
        'mx.DateTime',        # Legacy 1990s datetime library
        'pysqlite2',          # Python 2 era SQLite driver (Python 3 uses built-in sqlite3)
        'MySQLdb',            # MySQL driver (project uses SQLite/PostgreSQL)
        # Windows-specific modules (exclude when building on Linux/Mac)
        # These may be scanned by PyInstaller's ctypes detection but aren't needed
    ] + ([] if is_windows else [
        '_winreg',            # Windows registry access
        'winreg',             # Windows registry access (Python 3)
        'msvcrt',             # Microsoft Visual C Runtime
    ]),
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Build PYZ archive
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# Build executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='automagik-omni-backend',            # Executable name
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,                              # Console mode (not windowed)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/resources/build/icon.ico' if is_windows else None,  # Add Omni icon on Windows
)
