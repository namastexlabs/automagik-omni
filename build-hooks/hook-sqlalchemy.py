"""
PyInstaller hook for SQLAlchemy
Overrides default hook to exclude optional database drivers
"""
from PyInstaller.utils.hooks import collect_submodules, collect_all

# Collect SQLAlchemy modules but exclude optional drivers
hiddenimports = collect_submodules('sqlalchemy', filter=lambda name: not any([
    'mx' in name,
    'MySQLdb' in name,
    'pysqlite2' in name,
]))

# Explicitly exclude optional imports that trigger warnings
excludedimports = [
    'mx',
    'mx.DateTime',
    'MySQLdb',
    'pysqlite2',
    '_mysql',
]

# Collect data files
datas, binaries, _ = collect_all('sqlalchemy')
