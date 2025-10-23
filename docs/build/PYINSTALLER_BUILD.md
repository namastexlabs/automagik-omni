# PyInstaller Build Guide for Automagik Omni Backend

This guide explains how to build a standalone executable for the Automagik Omni backend using PyInstaller.

## Prerequisites

1. **Python 3.12** - The project requires Python 3.12 or higher
2. **PyInstaller** - Install with: `pip install pyinstaller` or `uv pip install pyinstaller`
3. **Project dependencies** - Ensure all dependencies are installed: `uv sync`

## Quick Build

From the project root directory:

```bash
pyinstaller automagik-omni-backend.spec
```

The built executable will be located at:
```
dist/automagik-omni-backend
```

## What Gets Bundled

The spec file bundles:

- **All Python source code** from `src/`
- **Database migrations** from `alembic/`
- **Alembic configuration** (`alembic.ini`)
- **Example environment file** (`.env.example`)
- **All required Python packages** and their dependencies

### Key Dependencies Included

- FastAPI + Uvicorn (ASGI server)
- Pydantic (data validation)
- SQLAlchemy + Alembic (database ORM and migrations)
- Typer + Rich (CLI framework)
- HTTPX + Requests (HTTP clients)
- Discord.py (if installed - optional)
- Boto3 (AWS SDK)
- Pika (RabbitMQ client)
- psycopg2-binary (PostgreSQL driver)

## Build Options

### Clean Build

Remove previous build artifacts before building:

```bash
rm -rf build/ dist/
pyinstaller automagik-omni-backend.spec
```

### Debug Build

For troubleshooting, enable debug mode by editing `automagik-omni-backend.spec`:

```python
exe = EXE(
    ...
    debug=True,  # Change from False to True
    ...
)
```

## Running the Executable

### Basic Usage

```bash
# Run from dist directory
./dist/automagik-omni-backend

# Or make it executable and run from anywhere
chmod +x dist/automagik-omni-backend
./dist/automagik-omni-backend
```

### With Environment Configuration

The executable still requires environment variables. Create a `.env` file in the same directory:

```bash
cd dist/
cp ../.env.example .env
# Edit .env with your configuration
./automagik-omni-backend
```

Or pass environment variables directly:

```bash
AUTOMAGIK_OMNI_API_HOST=0.0.0.0 \
AUTOMAGIK_OMNI_API_PORT=8000 \
./dist/automagik-omni-backend
```

## Database Setup

The executable includes Alembic migrations, but you need to ensure the database is initialized:

```bash
# The application will create tables on startup via create_tables()
# For Alembic migrations, you may need to run them separately or
# ensure the database URL is properly configured in your .env
```

## Troubleshooting

### Missing Modules

If you get "ModuleNotFoundError" when running the executable:

1. Identify the missing module
2. Add it to `hiddenimports` in `automagik-omni-backend.spec`
3. Rebuild with `pyinstaller automagik-omni-backend.spec`

Example:
```python
hiddenimports += ['missing_module_name']
```

### Import Errors for Dynamic Imports

Some packages use dynamic imports that PyInstaller can't detect. Add them explicitly:

```python
hiddenimports += collect_submodules('package_name')
```

### Binary Compatibility Issues

If the executable doesn't run on different systems:

- Build on the oldest supported OS version
- Use `--target-arch` flag for cross-compilation (limited support)
- Consider building separate executables for each platform

### Large Executable Size

The single-file executable can be large (100MB+). To reduce size:

1. Remove unused packages from dependencies
2. Use `upx=True` (already enabled) for compression
3. Consider using `--onedir` mode instead of `--onefile`:

```python
exe = EXE(
    pyz,
    a.scripts,
    # Remove these for --onedir mode:
    # a.binaries,
    # a.zipfiles,
    # a.datas,
    ...
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='automagik-omni-backend',
)
```

## Platform-Specific Notes

### Linux
- The executable is built for the current architecture (x86_64, ARM, etc.)
- May require system libraries like `libpq` for PostgreSQL support
- Test on target distribution before deploying

### Windows
- Build on Windows to create `.exe` executable
- May need Visual C++ Redistributable on target systems
- Antivirus may flag the executable (submit for whitelisting if needed)

### macOS
- Build on macOS to create macOS executable
- Code signing may be required for distribution
- Notarization needed for macOS 10.15+

## Distribution

When distributing the executable:

1. **Include documentation**: Provide `.env.example` and setup instructions
2. **System requirements**: Document Python version (for reference) and OS
3. **Dependencies**: Note external requirements (PostgreSQL, RabbitMQ if used)
4. **License**: Include `LICENSE` file if distributing

## Alternative: Using uvx

For end users, you might prefer distributing via `uvx`:

```bash
uvx --from /path/to/automagik-omni automagik-omni
```

This doesn't require PyInstaller and works across platforms, but requires Python/uv on the target system.

## Support

For issues specific to PyInstaller bundling:
- Check PyInstaller documentation: https://pyinstaller.org/
- Review PyInstaller hooks for your dependencies
- Test in a clean virtual environment

For Automagik Omni issues:
- See main `README.md`
- Check project documentation in `docs/`
- Review `CLAUDE.md` for development guidelines
