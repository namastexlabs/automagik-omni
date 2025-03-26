"""
FastAPI application for receiving Evolution API webhooks.
"""

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from src.config import config
from src.services.agent_service import agent_service
from src.channels.whatsapp.evolution_api_sender import evolution_api_sender, PresenceUpdater

# Configure logging
logger = logging.getLogger("src.api.app")

# Create FastAPI app
app = FastAPI(
    title="Omni Hub API",
    description="API for receiving webhooks from Evolution API",
    version="0.1.0"
)

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

@app.post("/webhook/evolution")
async def evolution_webhook(request: Request):
    """
    Webhook endpoint for Evolution API.
    Receives webhook events from Evolution API and processes them.
    """
    try:
        # Get the JSON data from the request
        data = await request.json()
        logger.info(f"Received webhook from Evolution API")
        logger.debug(f"Webhook data: {data}")
        
        # Update the Evolution API sender with the webhook data
        evolution_api_sender.update_from_webhook(data)
        
        # Extract the sender (for responses)
        sender = None
        if "data" in data and "key" in data["data"] and "remoteJid" in data["data"]["key"]:
            sender = data["data"]["key"]["remoteJid"]
        
        # Start typing indicator if we have a sender
        presence_updater = None
        if sender:
            presence_updater = PresenceUpdater(evolution_api_sender, sender)
            presence_updater.start()
        
        try:
            # Process the message
            response = agent_service.process_whatsapp_message(data)
            
            # Send response back if we have one
            if response and sender:
                # Send message
                evolution_api_sender.send_text_message(sender, response)
                
                # Stop typing indicator
                if presence_updater:
                    presence_updater.mark_message_sent()
                    presence_updater.stop()
            
            # Return response
            return {"status": "success", "response": response}
            
        finally:
            # Ensure typing indicator is stopped if it exists
            if presence_updater:
                presence_updater.stop()
                
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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