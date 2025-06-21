"""
FastAPI application for receiving Evolution API webhooks.
"""

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.config import config
from src.services.agent_service import agent_service
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender
from src.api.deps import get_database, get_instance_by_name
from src.api.routes.instances import router as instances_router
from src.db.database import create_tables
from src.db.bootstrap import ensure_default_instance

# Configure logging
logger = logging.getLogger("src.api.app")

# Create database tables on startup
create_tables()

# Create FastAPI app
app = FastAPI(
    title="Omni Hub API",
    description="Multi-tenant API for receiving webhooks from Evolution API",
    version="0.2.0"
)

# Include instance management routes
app.include_router(instances_router, prefix="/api/v1", tags=["instances"])

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

async def _handle_evolution_webhook(instance_config, request: Request):
    """
    Core webhook handling logic shared between default and tenant endpoints.
    
    Args:
        instance_config: InstanceConfig object with per-instance configuration
        request: FastAPI request object
    """
    try:
        # Get the JSON data from the request
        data = await request.json()
        logger.info(f"Received webhook for instance '{instance_config.name}'")
        logger.debug(f"Webhook data: {data}")
        
        # Update the Evolution API sender with the webhook data
        # This sets the runtime configuration from the webhook payload
        evolution_api_sender.update_from_webhook(data)
        
        # Process the message through the agent service
        # The agent service will now delegate to the WhatsApp handler
        # which will handle transcription and sending responses directly
        # TODO: Pass instance_config to service for per-instance agent configuration
        agent_service.process_whatsapp_message(data)
        
        # Return success response
        return {"status": "success", "instance": instance_config.name}
        
    except Exception as e:
        logger.error(f"Error processing webhook for instance '{instance_config.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/evolution")
async def evolution_webhook_default(
    request: Request,
    db: Session = Depends(get_database)
):
    """
    Default webhook endpoint for Evolution API (backward compatibility).
    Uses the default instance configuration.
    """
    # Get default instance configuration
    default_instance = ensure_default_instance(db)
    
    # Handle using shared logic
    return await _handle_evolution_webhook(default_instance, request)


@app.post("/webhook/evolution/{instance_name}")
async def evolution_webhook_tenant(
    instance_name: str,
    request: Request,
    db: Session = Depends(get_database)
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
    
    host = config.api.host if hasattr(config, 'api') and hasattr(config.api, 'host') else "0.0.0.0"
    port = config.api.port if hasattr(config, 'api') and hasattr(config.api, 'port') else 8000
    
    logger.info(f"Starting FastAPI server on {host}:{port}")
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=False
    ) 