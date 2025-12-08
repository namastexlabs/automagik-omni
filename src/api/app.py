"""
FastAPI application for receiving Evolution API webhooks.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import json
import time

# Import and set up logging
from fastapi.openapi.utils import get_openapi

from src.logger import setup_logging

# Set up logging with defaults from config
setup_logging()

# Configure logging
logger = logging.getLogger("src.api.app")

_MIGRATIONS_READY = False


def _ensure_database_ready(*, force: bool = False) -> float:
    """Ensure database schema is up to date, returning runtime in seconds."""

    global _MIGRATIONS_READY

    if _MIGRATIONS_READY and not force:
        return 0.0

    environment = os.environ.get("ENVIRONMENT")

    if environment == "test":
        _MIGRATIONS_READY = True
        return 0.0

    from src.db.migrations import auto_migrate

    logger.info("Running database migrations (first launch may take longer)...")
    start_time = time.perf_counter()

    if not auto_migrate():
        logger.error("❌ Database migrations failed during module initialization")
        _MIGRATIONS_READY = False
        raise RuntimeError("Database migrations must succeed before startup")

    duration = time.perf_counter() - start_time
    logger.info(f"✅ Database migrations ready in {duration:.2f}s")
    _MIGRATIONS_READY = True
    return duration


def prepare_runtime() -> float:
    """Public helper used by the CLI to warm database state before starting the API."""

    return _ensure_database_ready()


from src.core.telemetry import track_api_request, track_webhook_processed
from src.config import config
from src.services.agent_service import agent_service
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
from src.api.deps import get_database, get_instance_by_name
from src.api.routes.instances import router as instances_router
from src.api.routes.omni import router as omni_router
from src.api.routes.access import router as access_router
from src.db.database import create_tables, SessionLocal
from src.utils.datetime_utils import utcnow


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all incoming API requests with payload."""

    async def dispatch(self, request: Request, call_next):
        # Skip logging for health check and docs
        if request.url.path in [
            "/health",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
        ]:
            return await call_next(request)

        start_time = time.time()

        # Log request details
        logger.info(f"API Request: {request.method} {request.url.path}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request query params: {dict(request.query_params)}")

        # Log request body for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Read body
                body = await request.body()
                if body:
                    try:
                        # Try to parse as JSON
                        json_body = json.loads(body.decode())
                        # Mask sensitive fields
                        masked_body = self._mask_sensitive_data(json_body)
                        logger.debug(f"Request body: {json.dumps(masked_body, indent=2)}")
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        logger.debug(f"Request body (non-JSON): {len(body)} bytes")

                # Create new request with body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}

                request._receive = receive
            except Exception as e:
                logger.warning(f"Failed to log request body: {e}")

        # Process request
        response = await call_next(request)

        # Log response
        process_time = time.time() - start_time
        logger.info(f"API Response: {response.status_code} - {process_time:.3f}s")

        # Track API request telemetry
        try:
            track_api_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=process_time * 1000,
            )
        except Exception as e:
            # Never let telemetry break the API
            logger.debug(f"Telemetry tracking failed: {e}")

        return response

    def _mask_sensitive_data(self, data):
        """Mask sensitive fields and large payloads in request data."""
        if not isinstance(data, dict):
            return data

        masked = data.copy()
        sensitive_fields = [
            "password",
            "api_key",
            "agent_api_key",
            "evolution_key",
            "token",
            "secret",
        ]
        large_data_fields = ["base64", "message", "media_contents", "data"]

        for key, value in masked.items():
            if any(field in key.lower() for field in sensitive_fields):
                if isinstance(value, str) and len(value) > 8:
                    masked[key] = f"{value[:4]}***{value[-4:]}"
                elif isinstance(value, str) and value:
                    masked[key] = "***"
            elif any(field in key.lower() for field in large_data_fields):
                if isinstance(value, str) and len(value) > 100:
                    masked[key] = f"<large_string:{len(value)}_chars:{value[:20]}...{value[-20:]}>"
                elif isinstance(value, list) and len(value) > 0:
                    masked[key] = f"<array:{len(value)}_items>"
                elif isinstance(value, dict):
                    masked[key] = self._mask_sensitive_data(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)

        return masked


class LazyDBInitMiddleware(BaseHTTPMiddleware):
    """Middleware to defer database migrations until first request (saves ~2.5s startup)."""

    async def dispatch(self, request: Request, call_next):
        # Run migrations on first non-health request
        if not _MIGRATIONS_READY and request.url.path != "/health":
            logger.info("First request detected, running database migrations...")
            try:
                _ensure_database_ready()
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise HTTPException(status_code=503, detail="Database initialization failed")

        return await call_next(request)


# Note: create_tables() has been moved to lifespan function to ensure proper test isolation
# Database tables will be created during app startup in the lifespan function


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info("Initializing application...")
    # Skip database setup in test environment (handled by test fixtures)
    environment = os.environ.get("ENVIRONMENT")

    if environment != "test":
        # Database initialization moved to middleware (lazy init on first request)
        # This saves ~2.5s on cold start - migrations run only when needed

        # Still create tables structure for runtime checks (fast operation)
        try:
            create_tables()
            logger.info("✅ Database tables structure created/verified (migrations deferred to first request)")
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            # Let the app continue - tables might already exist

        # Load access control rules into cache
        try:
            from src.services.access_control import access_control_service

            with SessionLocal() as db:
                access_control_service.load_rules(db)
            logger.info("✅ Access control rules loaded into cache")
        except Exception as e:
            logger.error(f"❌ Failed to load access control rules: {e}")
            # Continue without access control cache - will be loaded on first use

        # Bootstrap global settings (auto-generate Evolution API key if needed)
        try:
            from src.db.bootstrap_settings import bootstrap_global_settings

            with SessionLocal() as db:
                bootstrap_global_settings(db)
            logger.info("✅ Global settings bootstrapped")
        except Exception as e:
            logger.error(f"❌ Failed to bootstrap global settings: {e}")
            # Continue - settings will be created on first use if needed
    else:
        logger.info("Skipping database setup in test environment")


    logger.info(f"Log level set to: {config.logging.level}")
    logger.info(f"API Host: {config.api.host}")
    logger.info(f"API Port: {config.api.port}")
    logger.info(f"API URL: http://{config.api.host}:{config.api.port}")

    # Auto-discover existing Evolution instances (non-intrusive)
    # Skip auto-discovery in test environment AND during onboarding
    if environment != "test":
        # Check if setup is complete - skip discovery during onboarding
        # This prevents race conditions where services try to connect before wizard finishes
        from src.services.settings_service import settings_service

        setup_complete = False
        try:
            with SessionLocal() as db:
                setup_setting = settings_service.get_setting("setup_completed", db)
                setup_complete = setup_setting and setup_setting.value.lower() in ("true", "1", "yes")
        except Exception:
            pass  # Database might not be ready yet during bootstrap

        if not setup_complete:
            logger.info("Skipping Evolution auto-discovery during onboarding (setup not complete)")
        else:
            # Initial discovery attempt (may fail if Evolution not ready yet)
            initial_discovered = []
            try:
                logger.info("Starting Evolution instance auto-discovery...")
                from src.services.discovery_service import discovery_service

                with SessionLocal() as db:
                    initial_discovered = await discovery_service.discover_evolution_instances(db)
                    if initial_discovered:
                        logger.info(f"Auto-discovered {len(initial_discovered)} Evolution instances:")
                        for instance in initial_discovered:
                            logger.info(f"  - {instance.name} (active: {instance.is_active})")
                    else:
                        logger.info("No new Evolution instances discovered")
            except Exception as e:
                logger.warning(f"Evolution instance auto-discovery failed: {e}")
                logger.debug(f"Auto-discovery error details: {str(e)}")
                logger.info("Continuing without auto-discovery - instances can be created manually")

            # Schedule delayed re-discovery to catch Evolution after it starts
            # This ensures webhook URLs are synced even if initial discovery failed
            async def delayed_discovery_and_webhook_sync():
                """Re-run discovery after Evolution has had time to start."""
                import asyncio
                await asyncio.sleep(30)  # Wait for Evolution to start (it needs subprocess-config first)

                try:
                    logger.info("Running delayed discovery and webhook sync...")
                    from src.services.discovery_service import discovery_service

                    with SessionLocal() as db:
                        discovered = await discovery_service.discover_evolution_instances(db)
                        if discovered:
                            logger.info(f"Delayed discovery found {len(discovered)} instances - webhooks synced")
                        else:
                            logger.debug("Delayed discovery found no instances")
                except Exception as e:
                    logger.warning(f"Delayed discovery failed: {e}")

            # Start delayed discovery task (non-blocking)
            import asyncio
            asyncio.create_task(delayed_discovery_and_webhook_sync())
    else:
        logger.info("Skipping Evolution instance auto-discovery in test environment")

    # Telemetry status logging
    from src.core.telemetry import telemetry_client

    if telemetry_client.is_enabled():
        logger.info("📊 Telemetry enabled - Anonymous usage analytics help improve Automagik Omni")
        logger.info("   • Collected: CLI usage, API performance, system info (no personal data)")
        logger.info("   • Disable: 'automagik-omni telemetry disable' or AUTOMAGIK_OMNI_DISABLE_TELEMETRY=true")
    else:
        logger.info("📊 Telemetry disabled")

    # Application ready - instances will be created via API endpoints
    logger.info("API ready - use /api/v1/instances to create instances")

    yield

    # Shutdown (cleanup if needed)
    logger.info("Shutting down application...")


# Create FastAPI app with authentication configuration
app = FastAPI(
    lifespan=lifespan,
    title=config.api.title,
    description=config.api.description,
    version=config.api.version,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=[
        {
            "name": "Instance Management",
            "description": "Create, configure, and monitor messaging channel instances.",
        },
        {
            "name": "Omni Channel Abstraction",
            "description": "Unified channel access to contacts and chats across providers.",
        },
        {
            "name": "messages",
            "description": "Message Operations",
        },
        {
            "name": "traces",
            "description": "Message Tracing & Analytics",
        },
        {
            "name": "webhooks",
            "description": "Webhook Receivers",
        },
        {
            "name": "profiles",
            "description": "User Profile Management",
        },
        {
            "name": "health",
            "description": "System Health & Status",
        },
    ],
)

# Include setup routes (unauthenticated, for onboarding)
from src.api.routes.setup import router as setup_router

app.include_router(setup_router, prefix="/api/v1", tags=["Setup"])

# Include omni communication routes under instances namespace (for unified API)
app.include_router(
    omni_router,
    prefix="/api/v1/instances",
    tags=["Omni Channel Abstraction"],
)

# Include instance management routes
app.include_router(
    instances_router,
    prefix="/api/v1",
    tags=["Instance Management"],
)


# Include trace management routes
from src.api.routes.traces import router as traces_router

app.include_router(traces_router, prefix="/api/v1", tags=["traces"])

# Include message sending routes
from src.api.routes.messages import router as messages_router

app.include_router(messages_router, prefix="/api/v1/instance", tags=["messages"])

# Include access control management routes
app.include_router(access_router, prefix="/api/v1", tags=["access"])

# Include global settings management routes
from src.api.routes.settings import router as settings_router

app.include_router(settings_router, prefix="/api/v1", tags=["settings"])

# Include database configuration routes (for wizard UI)
from src.api.routes.database_config import router as database_config_router

app.include_router(database_config_router, prefix="/api/v1", tags=["Database Configuration"])

# Include recovery routes (localhost-only API key recovery)
from src.api.routes.recovery import router as recovery_router

app.include_router(recovery_router, prefix="/api/v1", tags=["Recovery"])

# Include internal routes (localhost-only service-to-service communication)
from src.api.routes.internal import router as internal_router

app.include_router(internal_router, prefix="/api/v1", tags=["Internal"])

# Include sync routes (localStorage + PostgreSQL sync for settings)
from src.api.routes.sync import router as sync_router

app.include_router(sync_router, prefix="/api/v1", tags=["Sync"])

# Note: MCP server now runs as standalone service on port 18880
# Gateway proxies /mcp requests directly to standalone MCP server

# Add lazy DB initialization middleware (runs before other middleware)
app.add_middleware(LazyDBInitMiddleware)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors.allowed_origins,
    allow_credentials=config.cors.allow_credentials,
    allow_methods=config.cors.allow_methods,
    allow_headers=config.cors.allow_headers,
)


# Custom OpenAPI schema with enhanced formatting and authentication
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    # Enhanced API description
    enhanced_description = f"""
{config.api.description}

## Features

- Multi-tenant architecture with isolated instances
- Universal messaging across WhatsApp, Discord, and Slack
- Message tracing and analytics
- API key authentication via x-api-key header

## Quick Start

1. Include API key in `x-api-key` header
2. Create an instance for your channel
3. Send messages using the omni endpoints
4. Monitor activity via traces and health endpoints
"""

    openapi_schema = get_openapi(
        title=config.api.title,
        version=config.api.version,
        description=enhanced_description,
        routes=app.routes,
    )

    # Add server information dynamically from configuration
    servers = []

    # Add production server if configured
    if config.api.prod_server_url:
        servers.append(
            {
                "url": config.api.prod_server_url,
                "description": "Production Server",
            }
        )

    # Always add local development server with actual configured port
    servers.append(
        {
            "url": f"http://localhost:{config.api.port}",
            "description": "Local Development Server",
        }
    )

    openapi_schema["servers"] = servers

    # Add ApiKeyAuth security scheme
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    # Replace any existing security scheme with ApiKeyAuth
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "x-api-key",
            "description": "API key for authentication (e.g., 'namastex888')",
        }
    }

    # Update security requirement for all operations
    for path in openapi_schema.get("paths", {}).values():
        for operation in path.values():
            if isinstance(operation, dict) and "security" in operation:
                # Update existing security to use ApiKeyAuth
                operation["security"] = [{"ApiKeyAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Store API start time for uptime calculation
_api_start_time = time.time()


@app.get("/health", tags=["health"])
async def health_check():
    """
    System health check endpoint.

    Returns status for API, database, Discord services, and runtime information.
    """
    import os
    import resource
    import subprocess
    from datetime import datetime, timezone
    from src.db import get_engine

    # Get PID
    pid = os.getpid()

    # Get memory usage (in MB)
    try:
        mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux, ru_maxrss is in KB; on macOS it's in bytes
        import platform
        if platform.system() == 'Darwin':
            memory_mb = round(mem_usage / 1024 / 1024, 1)
        else:
            memory_mb = round(mem_usage / 1024, 1)
    except Exception:
        memory_mb = None

    # Get CPU percentage using ps command
    cpu_percent = 0.0
    try:
        result = subprocess.run(
            ['ps', '-p', str(pid), '-o', '%cpu', '--no-headers'],
            capture_output=True, text=True, timeout=1
        )
        cpu_percent = round(float(result.stdout.strip()), 1)
    except Exception:
        pass

    # Get database pool stats
    db_pool_stats = None
    try:
        engine = get_engine()
        pool = engine.pool
        if hasattr(pool, 'checkedout') and hasattr(pool, 'size'):
            db_pool_stats = {
                "pool_size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow() if hasattr(pool, 'overflow') else 0,
                "checked_in": pool.checkedin() if hasattr(pool, 'checkedin') else None,
            }
    except Exception:
        pass

    # Calculate uptime
    uptime_seconds = round(time.time() - _api_start_time)

    # Basic API health
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": {
                "status": "up",
                "uptime": uptime_seconds,
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
                "pid": pid,
                "checks": {"database": "connected", "runtime": "operational"},
            }
        },
    }

    # Add database pool stats if available
    if db_pool_stats:
        health_status["services"]["database"] = {
            "status": "connected",
            **db_pool_stats,
        }

    # Check Discord service status if available
    try:
        # Access Discord bot manager via the exported discord_service
        from src.services.discord_service import discord_service

        bot_manager = getattr(discord_service, "bot_manager", None)

        if bot_manager:
            bot_statuses = {}
            for instance_name in bot_manager.bots.keys():
                bot_status = bot_manager.get_bot_status(instance_name)
                if bot_status:
                    bot_statuses[instance_name] = {
                        "status": bot_status.status,
                        "guild_count": bot_status.guild_count,
                        "uptime": (bot_status.uptime.isoformat() if bot_status.uptime else None),
                        "latency": (round(bot_status.latency * 1000, 2) if bot_status.latency else None),  # ms
                    }

            health_status["services"]["discord"] = {
                "status": "up" if bot_statuses else "down",
                "instances": bot_statuses,
                "voice_sessions": len(bot_manager.voice_manager.get_voice_sessions()),
            }
        else:
            health_status["services"]["discord"] = {
                "status": "not_running",
                "message": "Discord service not initialized",
            }

    except Exception as e:
        health_status["services"]["discord"] = {"status": "error", "error": str(e)}

    return health_status


async def _handle_evolution_webhook(instance_config, request: Request, db: Session):
    """
    Core webhook handling logic shared between default and tenant endpoints.

    Args:
        instance_config: InstanceConfig object with per-instance configuration
        request: FastAPI request object
    """
    from src.services.trace_service import get_trace_context

    start_time = time.time()
    payload_size = 0

    try:
        logger.info(f"🔄 WEBHOOK ENTRY: Starting webhook processing for instance '{instance_config.name}'")

        # Get the JSON data from the request
        data = await request.json()
        payload_size = len(json.dumps(data).encode("utf-8"))
        logger.info(f"✅ WEBHOOK JSON PARSED: Received webhook for instance '{instance_config.name}'")

        # Enhanced logging for audio message debugging
        message_obj = data.get("data", {}).get("message", {})
        if "audioMessage" in message_obj:
            logger.info(f"🎵 AUDIO MESSAGE DETECTED: {json.dumps(message_obj, indent=2)[:1000]}")

        logger.debug(f"Webhook data: {data}")

        # Start message tracing
        with get_trace_context(data, instance_config.name, db) as trace:
            # Extract sender phone from webhook data for access control check
            sender_phone = data.get("data", {}).get("key", {}).get("remoteJid", "").split("@")[0]

            # Check access rules BEFORE processing the message
            from src.services.access_control import access_control_service

            has_access = access_control_service.check_access(
                phone_number=sender_phone,
                instance_name=instance_config.name,
                db=db,
            )

            if not has_access:
                # Message blocked by access rule
                if trace:
                    trace.update_trace_status(
                        status="access_denied",
                        blocked_by_access_rule=True,
                        blocking_reason=f"Blocked by access rule for phone {sender_phone}",
                        completed_at=utcnow(),
                    )
                logger.info(
                    f"🚫 Message from {sender_phone} blocked by access rule for instance {instance_config.name}"
                )
                return {
                    "status": "blocked",
                    "reason": "access_denied",
                    "phone": sender_phone,
                    "trace_id": trace.trace_id if trace else None,
                }

            # Update the Evolution API sender with the webhook data
            # This sets the runtime configuration from the webhook payload
            evolution_api_sender.update_from_webhook(data)

            # Override instance name with the correct one from our database config
            # to prevent URL conversion issues like "FlashinhoProTestonho" -> "flashinho-pro-testonho"
            evolution_api_sender.instance_name = instance_config.whatsapp_instance

            # Capture real media messages for testing purposes
            try:
                from src.utils.test_capture import test_capture

                test_capture.capture_media_message(data, instance_config)
            except Exception as e:
                logger.error(f"Test capture failed: {e}")

            # Process the message through the agent service
            # The agent service will now delegate to the WhatsApp handler
            # which will handle transcription and sending responses directly
            # Pass instance_config and trace context to service for per-instance agent configuration
            agent_service.process_whatsapp_message(data, instance_config, trace)

            # Track webhook processing telemetry
            try:
                track_webhook_processed(
                    channel="whatsapp",
                    success=True,
                    duration_ms=(time.time() - start_time) * 1000,
                    payload_size_kb=payload_size / 1024,
                    instance_type="multi_tenant",
                )
            except Exception as e:
                logger.debug(f"Webhook telemetry tracking failed: {e}")

            # Return success response
            return {
                "status": "success",
                "instance": instance_config.name,
                "trace_id": trace.trace_id if trace else None,
            }

    except Exception as e:
        # Track failed webhook processing
        try:
            track_webhook_processed(
                channel="whatsapp",
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                payload_size_kb=payload_size / 1024,
                instance_type="multi_tenant",
                error=str(e)[:100],  # Truncate error message
            )
        except Exception as te:
            logger.debug(f"Webhook telemetry tracking failed: {te}")

        logger.error(
            f"Error processing webhook for instance '{instance_config.name}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/evolution/{instance_name}", tags=["webhooks"])
async def evolution_webhook_tenant(instance_name: str, request: Request, db: Session = Depends(get_database)):
    """
    Multi-tenant webhook endpoint for Evolution API.

    Receives incoming messages from Evolution API instances and routes them to the appropriate tenant configuration.
    Supports text, media, audio, and other message types with automatic transcription and processing.
    """
    # Get instance configuration
    instance_config = get_instance_by_name(instance_name, db)

    # Handle using shared logic
    return await _handle_evolution_webhook(instance_config, request, db)


def start_api():
    """Start the FastAPI server using uvicorn."""
    import uvicorn

    host = config.api.host if hasattr(config, "api") and hasattr(config.api, "host") else "0.0.0.0"
    port = config.api.port if hasattr(config, "api") and hasattr(config.api, "port") else 8000

    logger.info(f"Starting FastAPI server on {host}:{port}")

    # Create custom logging config for uvicorn that completely suppresses its formatters
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "src.logger.ColoredFormatter",
                "fmt": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%H:%M:%S",
                "use_colors": True,
                "use_emojis": True,
                "shorten_paths": True,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "WARNING",
                "propagate": False,
            },
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["default"],
        },
    }

    uvicorn.run("src.api.app:app", host=host, port=port, reload=False, log_config=log_config)
