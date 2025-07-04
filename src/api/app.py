"""
FastAPI application for receiving Evolution API webhooks.
"""

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
import json
import time

# Import telemetry
from src.core.telemetry import track_api_request, track_webhook_processed, track_instance_operation

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
from src.db.database import create_tables

# Initialize channel handlers

# Configure logging
logger = logging.getLogger("src.api.app")


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
                        logger.debug(
                            f"Request body: {json.dumps(masked_body, indent=2)}"
                        )
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
                duration_ms=process_time * 1000
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
                    masked[key] = (
                        f"<large_string:{len(value)}_chars:{value[:20]}...{value[-20:]}>"
                    )
                elif isinstance(value, list) and len(value) > 0:
                    masked[key] = f"<array:{len(value)}_items>"
                elif isinstance(value, dict):
                    masked[key] = self._mask_sensitive_data(value)
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)

        return masked


# Create database tables on startup
create_tables()

# Create FastAPI app with authentication configuration
app = FastAPI(
    title=config.api.title,
    description=config.api.description,
    version=config.api.version,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=[
        {
            "name": "instances",
            "description": "Omnichannel instance management (WhatsApp, Slack, Discord)",
        },
        {
            "name": "messages",
            "description": "Message sending endpoints for all channel types",
        },
        {"name": "traces", "description": "Message tracing and analytics"},
        {"name": "webhooks", "description": "Webhook endpoints for receiving messages"},
        {"name": "health", "description": "Health check and status endpoints"},
    ],
)

# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])

# Include trace management routes
from src.api.routes.traces import router as traces_router

app.include_router(traces_router, prefix="/api/v1", tags=["traces"])

# Include message sending routes
try:
    from src.api.routes.messages import router as messages_router

    app.include_router(messages_router, prefix="/api/v1/instance", tags=["messages"])
    logger.info(
        f"✅ Messages router included with {len(messages_router.routes)} routes"
    )
except Exception as e:
    logger.error(f"❌ Failed to include messages router: {e}")
    import traceback

    logger.error(traceback.format_exc())

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom OpenAPI schema with Bearer token authentication
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=config.api.title,
        version=config.api.version,
        description=config.api.description,
        routes=app.routes,
    )

    # Add Bearer token authentication scheme
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your API key as a Bearer token",
    }

    # Apply security globally to all /api/v1 endpoints (except health)
    for path, path_item in openapi_schema.get("paths", {}).items():
        if path.startswith("/api/v1/") and path != "/health":
            for method, operation in path_item.items():
                if method.lower() in ["get", "post", "put", "delete", "patch"]:
                    if "security" not in operation:
                        operation["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Initialize default instance on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""

    logger.info("Initializing application...")
    logger.info(f"Log level set to: {config.logging.level}")
    logger.info(f"API Host: {config.api.host}")
    logger.info(f"API Port: {config.api.port}")
    logger.info(f"API URL: http://{config.api.host}:{config.api.port}")

    # Auto-discover existing Evolution instances (non-intrusive)
    try:
        logger.info("Starting Evolution instance auto-discovery...")
        from src.services.discovery_service import discovery_service
        from src.db.database import SessionLocal

        with SessionLocal() as db:
            discovered_instances = await discovery_service.discover_evolution_instances(
                db
            )
            if discovered_instances:
                logger.info(
                    f"Auto-discovered {len(discovered_instances)} Evolution instances:"
                )
                for instance in discovered_instances:
                    logger.info(f"  - {instance.name} (active: {instance.is_active})")
            else:
                logger.info("No new Evolution instances discovered")
    except Exception as e:
        logger.warning(f"Evolution instance auto-discovery failed: {e}")
        logger.debug(f"Auto-discovery error details: {str(e)}")
        logger.info(
            "Continuing without auto-discovery - instances can be created manually"
        )

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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/test/capture/enable")
async def enable_test_capture():
    """Enable test capture for the next media message."""
    from src.utils.test_capture import test_capture

    test_capture.enable_capture()
    return {
        "status": "enabled",
        "message": "Send a WhatsApp image/video to capture real test data",
    }


@app.post("/api/v1/test/capture/disable")
async def disable_test_capture():
    """Disable test capture."""
    from src.utils.test_capture import test_capture

    test_capture.disable_capture()
    return {"status": "disabled", "message": "Test capture disabled"}


@app.get("/api/v1/test/capture/status")
async def test_capture_status():
    """Get test capture status."""
    from src.utils.test_capture import test_capture

    return {
        "enabled": test_capture.capture_enabled,
        "directory": test_capture.save_directory,
    }


async def _handle_evolution_webhook(instance_config, request: Request):
    """
    Core webhook handling logic shared between default and tenant endpoints.

    Args:
        instance_config: InstanceConfig object with per-instance configuration
        request: FastAPI request object
    """
    from src.services.trace_service import get_trace_context
    
    start_time = time.time()
    success = True
    payload_size = 0

    try:
        # Get the JSON data from the request
        data = await request.json()
        payload_size = len(json.dumps(data).encode('utf-8'))
        logger.info(f"Received webhook for instance '{instance_config.name}'")
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
                    instance_type="multi_tenant"
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
        success = False
        
        # Track failed webhook processing
        try:
            track_webhook_processed(
                channel="whatsapp",
                success=False,
                duration_ms=(time.time() - start_time) * 1000,
                payload_size_kb=payload_size / 1024,
                instance_type="multi_tenant",
                error=str(e)[:100]  # Truncate error message
            )
        except Exception as te:
            logger.debug(f"Webhook telemetry tracking failed: {te}")
        
        logger.error(
            f"Error processing webhook for instance '{instance_config.name}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/evolution/{instance_name}")
async def evolution_webhook_tenant(
    instance_name: str, request: Request, db: Session = Depends(get_database)
):
    """
    Multi-tenant webhook endpoint for Evolution API.
    Uses per-instance configuration.
    """
    # Get instance configuration
    instance_config = get_instance_by_name(instance_name, db)

    # Handle using shared logic
    return await _handle_evolution_webhook(instance_config, request)


def start_api():
    """Start the FastAPI server using uvicorn."""
    import uvicorn

    host = (
        config.api.host
        if hasattr(config, "api") and hasattr(config.api, "host")
        else "0.0.0.0"
    )
    port = (
        config.api.port
        if hasattr(config, "api") and hasattr(config.api, "port")
        else 8000
    )

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

    uvicorn.run(
        "src.api.app:app", host=host, port=port, reload=False, log_config=log_config
    )
