"""
PyInstaller hook for Alembic
Excludes test-only modules to prevent collection warnings
"""
from PyInstaller.utils.hooks import collect_submodules

# Collect alembic modules but exclude testing modules
hiddenimports = collect_submodules('alembic', filter=lambda name: 'testing' not in name)

# Explicitly exclude test modules
excludedimports = [
    'alembic.testing',
    'alembic.testing.fixtures',
    'alembic.testing.env',
    'alembic.testing.plugin',
]
