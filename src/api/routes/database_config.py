"""
Database configuration API for wizard UI.

Provides endpoints to:
- Test PostgreSQL connection with tiered validation
- Get current database configuration
- Apply database configuration changes
"""

import logging
import socket
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.api.deps import verify_api_key
from src.services.settings_service import settings_service

logger = logging.getLogger(__name__)


def _set_or_update_setting(
    db,
    key: str,
    value: str,
    value_type: str,
    category: str,
    description: str,
    is_secret: bool = False,
) -> None:
    """Helper to create or update a setting."""
    existing = settings_service.get_setting(key, db)
    if existing:
        settings_service.update_setting(key, value, db)
    else:
        settings_service.create_setting(
            key=key,
            value=value,
            value_type=value_type,
            db=db,
            category=category,
            description=description,
            is_secret=is_secret,
        )


router = APIRouter(prefix="/database", tags=["Database Configuration"])


# Pydantic schemas


class DatabaseTestRequest(BaseModel):
    """Schema for database connection test request."""

    url: str = Field(..., description="PostgreSQL connection URL to test")


class TestResult(BaseModel):
    """Individual test result."""

    ok: bool
    message: str
    latency_ms: Optional[float] = None


class DatabaseTestResponse(BaseModel):
    """Schema for database connection test response."""

    success: bool
    tests: dict[str, TestResult]
    total_latency_ms: float


class DatabaseConfigResponse(BaseModel):
    """Schema for current database configuration (legacy, kept for backward compat)."""

    db_type: str
    use_postgres: bool
    postgres_url_configured: bool
    table_prefix: str
    pool_size: int
    pool_max_overflow: int


# New models for runtime vs saved state separation


class RuntimeDatabaseConfig(BaseModel):
    """Runtime configuration from frozen config object (set at startup from env vars).

    PostgreSQL only - SQLite is NOT supported.
    """

    db_type: str  # Always "postgresql"
    postgres_url_masked: Optional[str] = None
    table_prefix: str
    pool_size: int
    pool_max_overflow: int


class SavedDatabaseConfig(BaseModel):
    """Saved configuration from omni_global_settings table."""

    db_type: Optional[str] = None
    postgres_url_masked: Optional[str] = None
    postgres_host: Optional[str] = None
    postgres_port: Optional[str] = None
    postgres_database: Optional[str] = None
    redis_enabled: Optional[bool] = None
    redis_url_masked: Optional[str] = None
    redis_prefix_key: Optional[str] = None
    redis_ttl: Optional[int] = None
    redis_save_instances: Optional[bool] = None
    last_updated_at: Optional[str] = None


class DatabaseConfigurationState(BaseModel):
    """Complete database configuration state showing both runtime and saved config.

    This response allows the UI to:
    - Show what's currently running (runtime)
    - Show what's saved in settings (saved)
    - Display restart-required warnings when they differ
    - Show locked indicator when instances exist
    """

    # New structured response
    runtime: RuntimeDatabaseConfig
    saved: Optional[SavedDatabaseConfig] = None
    requires_restart: bool
    restart_required_reason: Optional[str] = None
    is_configured: bool  # True if setup wizard completed
    is_locked: bool  # True if instances exist (cannot change db_type)

    # Backward compatibility fields (deprecated - use runtime.* instead)
    db_type: str  # Always "postgresql"
    postgres_url_configured: bool
    table_prefix: str
    pool_size: int
    pool_max_overflow: int


class DatabaseApplyRequest(BaseModel):
    """Schema for applying database configuration.

    PostgreSQL only - SQLite is NOT supported.
    """

    postgres_url: str = Field(..., description="PostgreSQL connection URL")
    # Redis configuration
    redis_enabled: Optional[bool] = Field(False, description="Enable Redis cache")
    redis_url: Optional[str] = Field(None, description="Redis connection URL")
    redis_prefix_key: Optional[str] = Field("evolution", description="Redis key prefix")
    redis_ttl: Optional[int] = Field(604800, description="Redis TTL in seconds (default: 7 days)")
    redis_save_instances: Optional[bool] = Field(True, description="Save WhatsApp instances in Redis")


class DatabaseApplyResponse(BaseModel):
    """Schema for database apply response."""

    success: bool
    message: str
    requires_restart: bool


class RedisTestRequest(BaseModel):
    """Schema for Redis connection test request."""

    url: str = Field(..., description="Redis connection URL to test")


class RedisTestResponse(BaseModel):
    """Schema for Redis connection test response."""

    success: bool
    tests: dict[str, TestResult]
    total_latency_ms: float


class DetectedPostgresFields(BaseModel):
    """Detected PostgreSQL connection fields (password excluded)."""

    host: str
    port: str
    username: str
    database: str


class DetectedRedisFields(BaseModel):
    """Detected Redis connection fields (password excluded)."""

    host: str
    port: str
    dbNumber: str
    tls: bool


class EvolutionDetectResponse(BaseModel):
    """Schema for Evolution API database detection response."""

    found: bool
    source: Optional[str] = None
    message: str
    postgresql: Optional[DetectedPostgresFields] = None
    redis: Optional[DetectedRedisFields] = None


# Helper functions


def _test_tcp_connection(url: str) -> TestResult:
    """Test TCP connectivity to database server."""
    start = time.time()
    try:
        # Parse URL to extract host and port
        # postgresql://user:pass@host:port/dbname
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        latency = (time.time() - start) * 1000

        if result == 0:
            return TestResult(ok=True, message=f"TCP connection to {host}:{port} successful", latency_ms=latency)
        else:
            return TestResult(ok=False, message=f"Cannot reach {host}:{port} - connection refused")

    except socket.gaierror:
        return TestResult(ok=False, message="DNS resolution failed - hostname not found")
    except socket.timeout:
        return TestResult(ok=False, message="TCP connection timed out after 5 seconds")
    except Exception as e:
        return TestResult(ok=False, message=f"TCP test error: {str(e)}")


def _test_auth(url: str) -> TestResult:
    """Test database authentication."""
    start = time.time()
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()

        latency = (time.time() - start) * 1000
        return TestResult(ok=True, message="Authentication successful", latency_ms=latency)

    except OperationalError as e:
        error_str = str(e)
        if "authentication failed" in error_str.lower() or "password" in error_str.lower():
            return TestResult(ok=False, message="Authentication failed - invalid username or password")
        elif "does not exist" in error_str.lower():
            return TestResult(ok=False, message="Database does not exist")
        else:
            return TestResult(ok=False, message=f"Connection error: {error_str[:100]}")
    except Exception as e:
        return TestResult(ok=False, message=f"Auth test error: {str(e)[:100]}")


def _test_permissions(url: str) -> TestResult:
    """Test database permissions (CREATE TABLE capability)."""
    start = time.time()
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            # Try to create a temporary test table
            conn.execute(text("CREATE TABLE IF NOT EXISTS _omni_permission_test (id INT)"))
            conn.execute(text("DROP TABLE IF EXISTS _omni_permission_test"))
            conn.commit()
        engine.dispose()

        latency = (time.time() - start) * 1000
        return TestResult(ok=True, message="CREATE TABLE permission verified", latency_ms=latency)

    except ProgrammingError:
        return TestResult(ok=False, message="Insufficient permissions - cannot create tables")
    except Exception as e:
        return TestResult(ok=False, message=f"Permission test error: {str(e)[:100]}")


def _test_write_read(url: str) -> TestResult:
    """Test write/read operations."""
    start = time.time()
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            # Create, write, read, cleanup
            conn.execute(text("CREATE TABLE IF NOT EXISTS _omni_rw_test (id INT, val VARCHAR(50))"))
            conn.execute(text("INSERT INTO _omni_rw_test (id, val) VALUES (1, 'test')"))
            result = conn.execute(text("SELECT val FROM _omni_rw_test WHERE id = 1"))
            row = result.fetchone()
            conn.execute(text("DROP TABLE _omni_rw_test"))
            conn.commit()

            if row and row[0] == "test":
                latency = (time.time() - start) * 1000
                return TestResult(ok=True, message="Read/write operations verified", latency_ms=latency)
            else:
                return TestResult(ok=False, message="Read/write verification failed - data mismatch")

        engine.dispose()

    except Exception as e:
        return TestResult(ok=False, message=f"Read/write test error: {str(e)[:100]}")


def _ensure_database_exists(url: str) -> TestResult:
    """Create the database if it doesn't exist.

    Connects to the 'postgres' admin database to check/create the target database.
    """
    from urllib.parse import urlparse, urlunparse

    start = time.time()
    try:
        parsed = urlparse(url)
        db_name = parsed.path.lstrip("/")

        if not db_name:
            return TestResult(ok=False, message="No database name specified in URL")

        # Build admin URL pointing to 'postgres' database
        admin_parsed = parsed._replace(path="/postgres")
        admin_url = urlunparse(admin_parsed)

        # Connect to postgres admin database
        engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :db_name"), {"db_name": db_name})
            exists = result.fetchone() is not None

            if not exists:
                # Create the database
                # Use raw SQL since we need AUTOCOMMIT for CREATE DATABASE
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                latency = (time.time() - start) * 1000
                logger.info(f"Created database '{db_name}'")
                return TestResult(ok=True, message=f"Created database '{db_name}'", latency_ms=latency)
            else:
                latency = (time.time() - start) * 1000
                return TestResult(ok=True, message=f"Database '{db_name}' exists", latency_ms=latency)

        engine.dispose()

    except OperationalError as e:
        error_str = str(e)
        if "authentication failed" in error_str.lower() or "password" in error_str.lower():
            return TestResult(ok=False, message="Authentication failed - cannot create database")
        elif "permission denied" in error_str.lower():
            return TestResult(ok=False, message="Permission denied - user cannot create databases")
        else:
            return TestResult(ok=False, message=f"Database creation error: {error_str[:100]}")
    except ProgrammingError as e:
        if "permission denied" in str(e).lower():
            return TestResult(ok=False, message="Permission denied - user cannot create databases")
        return TestResult(ok=False, message=f"Database creation error: {str(e)[:100]}")
    except Exception as e:
        return TestResult(ok=False, message=f"Database creation error: {str(e)[:100]}")


# Redis Helper Functions


def _test_redis_tcp_connection(url: str) -> TestResult:
    """Test TCP connectivity to Redis server."""
    start = time.time()
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        latency = (time.time() - start) * 1000

        if result == 0:
            return TestResult(ok=True, message=f"TCP connection to {host}:{port} successful", latency_ms=latency)
        else:
            return TestResult(ok=False, message=f"Cannot reach {host}:{port} - connection refused")

    except socket.gaierror:
        return TestResult(ok=False, message="DNS resolution failed - hostname not found")
    except socket.timeout:
        return TestResult(ok=False, message="TCP connection timed out after 5 seconds")
    except Exception as e:
        return TestResult(ok=False, message=f"TCP test error: {str(e)}")


def _test_redis_auth(url: str) -> TestResult:
    """Test Redis authentication and basic operations."""
    start = time.time()
    try:
        import redis

        client = redis.from_url(url, socket_timeout=10)

        # Test PING
        response = client.ping()
        if not response:
            return TestResult(ok=False, message="Redis PING failed")

        latency = (time.time() - start) * 1000
        client.close()
        return TestResult(ok=True, message="Redis authentication successful", latency_ms=latency)

    except redis.AuthenticationError:
        return TestResult(ok=False, message="Authentication failed - invalid password")
    except redis.ConnectionError as e:
        return TestResult(ok=False, message=f"Connection error: {str(e)[:100]}")
    except Exception as e:
        return TestResult(ok=False, message=f"Redis auth test error: {str(e)[:100]}")


def _test_redis_write_read(url: str) -> TestResult:
    """Test Redis write/read operations."""
    start = time.time()
    try:
        import redis

        client = redis.from_url(url, socket_timeout=10)

        # Test SET/GET/DEL
        test_key = "_omni_redis_test"
        test_value = "test_value_" + str(time.time())

        client.set(test_key, test_value, ex=60)  # 60 second TTL
        retrieved = client.get(test_key)
        client.delete(test_key)

        if retrieved and retrieved.decode("utf-8") == test_value:
            latency = (time.time() - start) * 1000
            client.close()
            return TestResult(ok=True, message="Read/write operations verified", latency_ms=latency)
        else:
            client.close()
            return TestResult(ok=False, message="Read/write verification failed - data mismatch")

    except Exception as e:
        return TestResult(ok=False, message=f"Read/write test error: {str(e)[:100]}")


# API Endpoints


@router.get(
    "/config",
    response_model=DatabaseConfigurationState,
    summary="Get Database Configuration State",
    description="Get both runtime and saved database configuration with restart detection",
)
async def get_database_config(
    api_key: str = Depends(verify_api_key),
):
    """
    Get complete database configuration state.

    Returns:
        - runtime: Current frozen configuration from environment (set at startup)
        - saved: User-configured settings from database (set via wizard)
        - requires_restart: True if saved differs from runtime
        - is_locked: True if instances exist (cannot change db_type)
    """
    from src.db.database import get_db
    from src.services.database_state_service import database_state_service

    # Get a database session
    db_gen = get_db()
    db = next(db_gen)

    try:
        # Get both configurations
        runtime = database_state_service.get_runtime_config()
        saved = database_state_service.get_saved_config(db)

        # Check if restart is required
        requires_restart, reason = database_state_service.check_requires_restart(runtime, saved)

        # Check configuration status
        is_configured = database_state_service.is_setup_completed(db)
        is_locked = database_state_service.is_db_locked(db)

        return DatabaseConfigurationState(
            # New structured response
            runtime=RuntimeDatabaseConfig(
                db_type=runtime["db_type"],
                postgres_url_masked=runtime["postgres_url_masked"],
                table_prefix=runtime["table_prefix"],
                pool_size=runtime["pool_size"],
                pool_max_overflow=runtime["pool_max_overflow"],
            ),
            saved=SavedDatabaseConfig(**saved) if saved else None,
            requires_restart=requires_restart,
            restart_required_reason=reason,
            is_configured=is_configured,
            is_locked=is_locked,
            # Backward compatibility (deprecated)
            db_type=runtime["db_type"],
            postgres_url_configured=runtime["postgres_url_masked"] is not None,
            table_prefix=runtime["table_prefix"],
            pool_size=runtime["pool_size"],
            pool_max_overflow=runtime["pool_max_overflow"],
        )
    finally:
        db.close()


@router.post(
    "/test",
    response_model=DatabaseTestResponse,
    summary="Test Database Connection",
    description="Test PostgreSQL connection with tiered validation (TCP, auth, permissions, read/write). Public endpoint for onboarding.",
)
async def test_database_connection(
    request: DatabaseTestRequest,
):
    """
    Test PostgreSQL connection with tiered validation.

    Tests performed in order:
    1. TCP connectivity check
    2. Database creation (if doesn't exist)
    3. Authentication test
    4. Permission test (CREATE TABLE)
    5. Write/read test

    If any test fails, subsequent tests are skipped.
    """
    start_time = time.time()
    tests: dict[str, TestResult] = {}

    # Validate URL format
    if not request.url.startswith("postgresql://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with 'postgresql://'",
        )

    # Test 1: TCP connectivity
    tcp_result = _test_tcp_connection(request.url)
    tests["tcp"] = tcp_result

    if not tcp_result.ok:
        return DatabaseTestResponse(
            success=False,
            tests=tests,
            total_latency_ms=(time.time() - start_time) * 1000,
        )

    # Step 2: Ensure database exists (create if needed)
    db_create_result = _ensure_database_exists(request.url)
    tests["database"] = db_create_result

    if not db_create_result.ok:
        return DatabaseTestResponse(
            success=False,
            tests=tests,
            total_latency_ms=(time.time() - start_time) * 1000,
        )

    # Test 3: Authentication
    auth_result = _test_auth(request.url)
    tests["auth"] = auth_result

    if not auth_result.ok:
        return DatabaseTestResponse(
            success=False,
            tests=tests,
            total_latency_ms=(time.time() - start_time) * 1000,
        )

    # Test 4: Permissions
    perm_result = _test_permissions(request.url)
    tests["permissions"] = perm_result

    if not perm_result.ok:
        return DatabaseTestResponse(
            success=False,
            tests=tests,
            total_latency_ms=(time.time() - start_time) * 1000,
        )

    # Test 5: Write/Read
    rw_result = _test_write_read(request.url)
    tests["write_read"] = rw_result

    total_latency = (time.time() - start_time) * 1000
    all_passed = all(t.ok for t in tests.values())

    return DatabaseTestResponse(
        success=all_passed,
        tests=tests,
        total_latency_ms=total_latency,
    )


@router.post(
    "/redis/test",
    response_model=RedisTestResponse,
    summary="Test Redis Connection",
    description="Test Redis connection with tiered validation (TCP, auth, read/write). Public endpoint for onboarding.",
)
async def test_redis_connection(
    request: RedisTestRequest,
):
    """
    Test Redis connection with tiered validation.

    Tests performed in order:
    1. TCP connectivity check
    2. Authentication test (PING)
    3. Write/read test (SET/GET/DEL)

    If any test fails, subsequent tests are skipped.
    """
    start_time = time.time()
    tests: dict[str, TestResult] = {}

    # Validate URL format
    if not request.url.startswith("redis://") and not request.url.startswith("rediss://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL must start with 'redis://' or 'rediss://'",
        )

    # Test 1: TCP connectivity
    tcp_result = _test_redis_tcp_connection(request.url)
    tests["tcp"] = tcp_result

    if not tcp_result.ok:
        return RedisTestResponse(
            success=False,
            tests=tests,
            total_latency_ms=(time.time() - start_time) * 1000,
        )

    # Test 2: Authentication
    auth_result = _test_redis_auth(request.url)
    tests["auth"] = auth_result

    if not auth_result.ok:
        return RedisTestResponse(
            success=False,
            tests=tests,
            total_latency_ms=(time.time() - start_time) * 1000,
        )

    # Test 3: Write/Read
    rw_result = _test_redis_write_read(request.url)
    tests["write_read"] = rw_result

    total_latency = (time.time() - start_time) * 1000
    all_passed = all(t.ok for t in tests.values())

    return RedisTestResponse(
        success=all_passed,
        tests=tests,
        total_latency_ms=total_latency,
    )


@router.post(
    "/apply",
    response_model=DatabaseApplyResponse,
    summary="Apply Database Configuration",
    description="Apply database configuration (requires application restart)",
)
async def apply_database_config(
    request: DatabaseApplyRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Apply database configuration changes.

    Note: Changes are saved to settings but require application restart to take effect.
    The application uses environment variables for database configuration, so this
    endpoint stores the configuration in global settings for the wizard UI to use.

    PostgreSQL only - SQLite is NOT supported.
    """
    from src.db.database import get_db

    # Validate PostgreSQL URL format
    if not request.postgres_url.startswith("postgresql://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="postgres_url must start with 'postgresql://'",
        )

    try:
        # Get a database session for global settings
        db_gen = get_db()
        db = next(db_gen)

        try:
            # Store configuration in global settings (create or update)
            # PostgreSQL only - always set database_type to postgresql
            _set_or_update_setting(
                db,
                key="database_type",
                value="postgresql",
                value_type="string",
                category="database",
                description="Database type (postgresql only)",
            )

            # Save PostgreSQL URL
            _set_or_update_setting(
                db,
                key="postgres_url",
                value=request.postgres_url,
                value_type="secret",
                category="database",
                description="PostgreSQL connection URL",
                is_secret=True,
            )

            # Save Redis configuration
            if request.redis_enabled and request.redis_url:
                _set_or_update_setting(
                    db,
                    key="cache_redis_enabled",
                    value="true",
                    value_type="boolean",
                    category="cache",
                    description="Enable Redis cache for Evolution API",
                )
                _set_or_update_setting(
                    db,
                    key="cache_redis_uri",
                    value=request.redis_url,
                    value_type="secret",
                    category="cache",
                    description="Redis connection URL",
                    is_secret=True,
                )
                _set_or_update_setting(
                    db,
                    key="cache_redis_prefix_key",
                    value=request.redis_prefix_key or "evolution",
                    value_type="string",
                    category="cache",
                    description="Redis key prefix",
                )
                _set_or_update_setting(
                    db,
                    key="cache_redis_ttl",
                    value=str(request.redis_ttl or 604800),
                    value_type="integer",
                    category="cache",
                    description="Redis TTL in seconds",
                )
                _set_or_update_setting(
                    db,
                    key="cache_redis_save_instances",
                    value="true" if request.redis_save_instances else "false",
                    value_type="boolean",
                    category="cache",
                    description="Save WhatsApp instances in Redis",
                )
                _set_or_update_setting(
                    db,
                    key="cache_local_enabled",
                    value="false",
                    value_type="boolean",
                    category="cache",
                    description="Enable local cache (disabled when Redis is enabled)",
                )
            elif not request.redis_enabled:
                # Disable Redis, enable local cache
                _set_or_update_setting(
                    db,
                    key="cache_redis_enabled",
                    value="false",
                    value_type="boolean",
                    category="cache",
                    description="Enable Redis cache for Evolution API",
                )
                _set_or_update_setting(
                    db,
                    key="cache_local_enabled",
                    value="true",
                    value_type="boolean",
                    category="cache",
                    description="Enable local cache",
                )

            db.commit()

            # Build response message (PostgreSQL only)
            env_vars = ["AUTOMAGIK_OMNI_POSTGRES_URL"]
            if request.redis_enabled:
                env_vars.extend(
                    [
                        "CACHE_REDIS_ENABLED=true",
                        "CACHE_REDIS_URI",
                        f"CACHE_REDIS_PREFIX_KEY={request.redis_prefix_key or 'evolution'}",
                        f"CACHE_REDIS_TTL={request.redis_ttl or 604800}",
                        f"CACHE_REDIS_SAVE_INSTANCES={'true' if request.redis_save_instances else 'false'}",
                        "CACHE_LOCAL_ENABLED=false",
                    ]
                )

            return DatabaseApplyResponse(
                success=True,
                message=f"Configuration saved. Set the following environment variables and restart: {', '.join(env_vars)}",
                requires_restart=True,
            )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to apply database config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}",
        )


@router.get(
    "/detect-evolution",
    response_model=EvolutionDetectResponse,
    summary="Detect WhatsApp Web API Database",
    description="Attempt to detect WhatsApp Web API's database configuration with parsed field objects. Public endpoint for onboarding.",
)
async def detect_evolution_database():
    """
    Attempt to detect Evolution API's database configuration.

    Looks for common Evolution API environment variables and returns
    parsed connection fields (passwords excluded for security).
    """
    import os
    from urllib.parse import urlparse

    # Common Evolution API database env vars
    postgres_vars = [
        "DATABASE_CONNECTION_URI",
        "EVOLUTION_DATABASE_URL",
        "DATABASE_URL",
    ]

    redis_vars = [
        "CACHE_REDIS_URI",
        "REDIS_URI",
        "REDIS_URL",
    ]

    postgres_fields = None
    redis_fields = None
    source_var = None

    # Detect PostgreSQL configuration
    for var in postgres_vars:
        value = os.getenv(var)
        if value and value.startswith("postgresql://"):
            try:
                parsed = urlparse(value)
                postgres_fields = DetectedPostgresFields(
                    host=parsed.hostname or "localhost",
                    port=str(parsed.port) if parsed.port else "5432",
                    username=parsed.username or "",
                    database=parsed.pathname.lstrip("/") if parsed.pathname else "",
                )
                source_var = var
            except Exception as e:
                logger.error(f"Failed to parse PostgreSQL URL from {var}: {e}")
                continue
            break

    # Detect Redis configuration
    for var in redis_vars:
        value = os.getenv(var)
        if value and (value.startswith("redis://") or value.startswith("rediss://")):
            try:
                parsed = urlparse(value)
                redis_fields = DetectedRedisFields(
                    host=parsed.hostname or "localhost",
                    port=str(parsed.port) if parsed.port else "6379",
                    dbNumber=parsed.pathname.lstrip("/") if parsed.pathname else "0",
                    tls=value.startswith("rediss://"),
                )
                if not source_var:
                    source_var = var
            except Exception as e:
                logger.error(f"Failed to parse Redis URL from {var}: {e}")
                continue
            break

    # Build response
    if postgres_fields or redis_fields:
        parts = []
        if postgres_fields:
            parts.append(f"PostgreSQL at {postgres_fields.host}:{postgres_fields.port}")
        if redis_fields:
            parts.append(f"Redis at {redis_fields.host}:{redis_fields.port}")

        return EvolutionDetectResponse(
            found=True,
            source=source_var,
            message=f"Detected WhatsApp Web API configuration: {', '.join(parts)}",
            postgresql=postgres_fields,
            redis=redis_fields,
        )
    else:
        return EvolutionDetectResponse(
            found=False,
            source=None,
            message="No WhatsApp Web API database configuration detected",
            postgresql=None,
            redis=None,
        )
