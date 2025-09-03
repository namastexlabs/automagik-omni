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

# Import telemetry
from src.core.telemetry import track_api_request, track_webhook_processed

# Import configuration first to ensure environment variables are loaded
from src.config import config

# Import and set up logging
from src.logger import setup_logging

# Set up logging with defaults from config
setup_logging()

from src.services.agent_service import agent_service
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
from src.api.deps import get_database, get_instance_by_name
from fastapi.openapi.utils import get_openapi
from src.api.routes.instances import router as instances_router
from src.api.routes.omni import router as omni_router
from src.db.database import create_tables

# Configure logging
logger = logging.getLogger("src.api.app")

# Initialize channel handlers
# Note: Streaming functionality is now integrated directly into the handlers


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


# Note: create_tables() has been moved to lifespan function to ensure proper test isolation
# Database tables will be created during app startup in the lifespan function


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup
    logger.info("Initializing application...")
    logger.info(f"Log level set to: {config.logging.level}")
    logger.info(f"API Host: {config.api.host}")
    logger.info(f"API Port: {config.api.port}")
    logger.info(f"API URL: http://{config.api.host}:{config.api.port}")

    # Skip database setup in test environment (handled by test fixtures)
    if os.environ.get("ENVIRONMENT") != "test":
        # Create database tables
        try:
            create_tables()
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            # Let the app continue - tables might already exist

        # Run database migrations
        try:
            logger.info("Checking database migrations...")
            from src.db.migrations import auto_migrate

            if auto_migrate():
                logger.info("✅ Database migrations completed successfully")
            else:
                logger.error("❌ Database migrations failed")
                # Don't stop the application, but log the error
                logger.warning("Application starting despite migration issues - manual intervention may be required")
        except Exception as e:
            logger.error(f"❌ Database migration error: {e}")
            logger.warning("Application starting despite migration issues - manual intervention may be required")
    else:
        logger.info("Skipping database setup in test environment")

    # Auto-discover existing Evolution instances (non-intrusive)
    # Skip auto-discovery in test environment to prevent database conflicts
    if os.environ.get("ENVIRONMENT") != "test":
        try:
            logger.info("Starting Evolution instance auto-discovery...")
            from src.services.discovery_service import discovery_service
            from src.db.database import SessionLocal

            with SessionLocal() as db:
                discovered_instances = await discovery_service.discover_evolution_instances(db)
                if discovered_instances:
                    logger.info(f"Auto-discovered {len(discovered_instances)} Evolution instances:")
                    for instance in discovered_instances:
                        logger.info(f"  - {instance.name} (active: {instance.is_active})")
                else:
                    logger.info("No new Evolution instances discovered")
        except Exception as e:
            logger.warning(f"Evolution instance auto-discovery failed: {e}")
            logger.debug(f"Auto-discovery error details: {str(e)}")
            logger.info("Continuing without auto-discovery - instances can be created manually")
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
            "name": "instances",
            "description": "Instance Management",
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

# Include omni communication routes (register first to take precedence)
app.include_router(omni_router, prefix="/api/v1", tags=["instances"])

# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])


# Include trace management routes
from src.api.routes.traces import router as traces_router

app.include_router(traces_router, prefix="/api/v1", tags=["traces"])

# Include message sending routes
try:
    from src.api.routes.messages import router as messages_router

    app.include_router(messages_router, prefix="/api/v1/instance", tags=["messages"])
except Exception as e:
    logger.error(f"❌ Failed to include messages router: {e}")
    import traceback

    logger.error(traceback.format_exc())

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
- Bearer token authentication

## Quick Start

1. Include API key in `Authorization: Bearer <token>` header
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

    # Add server information with both production and local servers
    openapi_schema["servers"] = [
        {
            "url": "https://omni-mctech.namastex.ai",
            "description": "Production Server",
        },
        {
            "url": "http://localhost:8882",
            "description": "Local Development Server",
        }
    ]

    # Update the existing HTTPBearer security scheme with better description
    if "components" in openapi_schema and "securitySchemes" in openapi_schema["components"]:
        if "HTTPBearer" in openapi_schema["components"]["securitySchemes"]:
            openapi_schema["components"]["securitySchemes"]["HTTPBearer"]["description"] = (
                "Enter your API key as a Bearer token (e.g., 'namastex888')"
            )
            openapi_schema["components"]["securitySchemes"]["HTTPBearer"]["bearerFormat"] = "API Key"

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health", tags=["health"])
async def health_check():
    """
    System health check endpoint.

    Returns status for API, database, Discord services, and runtime information.
    """

    from datetime import datetime, timezone

    # Basic API health
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": {
                "status": "up",
                "checks": {"database": "connected", "runtime": "operational"},
            }
        },
    }

    # Check Discord service status if available
    try:
        # Get Discord bot manager instance (if running)
        from src.services.discord_service import discord_bot_manager

        if discord_bot_manager:
            bot_statuses = {}
            for instance_name in discord_bot_manager.bots.keys():
                bot_status = discord_bot_manager.get_bot_status(instance_name)
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
                "voice_sessions": len(discord_bot_manager.voice_manager.get_voice_sessions()),
            }
        else:
            health_status["services"]["discord"] = {
                "status": "not_running",
                "message": "Discord service not initialized",
            }

    except Exception as e:
        health_status["services"]["discord"] = {"status": "error", "error": str(e)}

    return health_status


async def _handle_evolution_webhook(instance_config, request: Request):
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
        with get_trace_context(data, instance_config.name) as trace:
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
    return await _handle_evolution_webhook(instance_config, request)


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
