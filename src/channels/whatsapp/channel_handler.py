"""
WhatsApp channel handler using Evolution API.
"""

import logging
from typing import Dict, Any
from src.channels.base import ChannelHandler, QRCodeResponse, ConnectionStatus
from src.channels.whatsapp.evolution_client import get_evolution_client, EvolutionCreateRequest
from src.db.models import InstanceConfig
from src.config import config

logger = logging.getLogger(__name__)


class WhatsAppChannelHandler(ChannelHandler):
    """WhatsApp channel handler implementation."""
    
    async def create_instance(self, instance: InstanceConfig, **kwargs) -> Dict[str, Any]:
        """Create a new WhatsApp instance in Evolution API or use existing one."""
        try:
            evolution_client = get_evolution_client()
            
            # First, check if an Evolution instance with this name already exists
            logger.info(f"Checking if Evolution instance '{instance.name}' already exists...")
            
            existing_instances = await evolution_client.fetch_instances(instance_name=instance.name)
            
            if existing_instances:
                # Instance already exists, use it
                existing_instance = existing_instances[0]
                logger.info(f"Evolution instance '{instance.name}' already exists, using existing instance")
                
                # Set webhook URL for existing instance if needed
                webhook_url = f"http://{config.api.host}:{config.api.port}/webhook/evolution/{instance.name}"
                
                try:
                    await evolution_client.set_webhook(instance.name, webhook_url)
                    logger.info(f"Updated webhook URL for existing instance: {webhook_url}")
                except Exception as webhook_error:
                    logger.warning(f"Failed to update webhook for existing instance: {webhook_error}")
                
                return {
                    "evolution_response": {"instance": existing_instance.dict(), "hash": {"apikey": existing_instance.apikey}},
                    "evolution_instance_id": existing_instance.instanceId,
                    "evolution_apikey": existing_instance.apikey,
                    "webhook_url": webhook_url,
                    "existing_instance": True
                }
            
            # Instance doesn't exist, create a new one
            logger.info(f"Creating new Evolution instance '{instance.name}'...")
            
            # Extract WhatsApp-specific parameters
            phone_number = kwargs.get("phone_number")
            auto_qr = kwargs.get("auto_qr", True)
            integration = kwargs.get("integration", "WHATSAPP-BAILEYS")
            
            # Set webhook URL automatically
            webhook_url = f"http://{config.api.host}:{config.api.port}/webhook/evolution/{instance.name}"
            
            # Prepare Evolution API request
            evolution_request = EvolutionCreateRequest(
                instanceName=instance.name,
                integration=integration,
                qrcode=auto_qr,
                number=phone_number,
                webhook={
                    "url": webhook_url,
                    "byEvents": True,
                    "base64": True,
                    "events": [
                        "QRCODE_UPDATED",
                        "CONNECTION_UPDATE", 
                        "MESSAGES_UPSERT",
                        "MESSAGES_UPDATE", 
                        "SEND_MESSAGE"
                    ]
                }
            )
            
            response = await evolution_client.create_instance(evolution_request)
            logger.info(f"WhatsApp instance created: {response}")
            
            return {
                "evolution_response": response,
                "evolution_instance_id": response.get("instance", {}).get("instanceId"),
                "evolution_apikey": response.get("hash", {}).get("apikey"),
                "webhook_url": webhook_url,
                "existing_instance": False
            }
            
        except Exception as e:
            logger.error(f"Failed to create WhatsApp instance: {e}")
            raise Exception(f"WhatsApp instance creation failed: {str(e)}")
    
    async def get_qr_code(self, instance: InstanceConfig) -> QRCodeResponse:
        """Get QR code for WhatsApp connection."""
        try:
            evolution_client = get_evolution_client()
            connect_response = await evolution_client.connect_instance(instance.name)
            
            qr_code = None
            message = "QR code not available"
            
            # Extract QR code from response
            if "qrcode" in connect_response:
                qr_code = connect_response["qrcode"].get("base64")
                message = "QR code ready for scanning"
            elif "message" in connect_response:
                message = connect_response["message"]
            
            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="whatsapp",
                qr_code=qr_code,
                status="success" if qr_code else "unavailable",
                message=message
            )
            
        except Exception as e:
            logger.error(f"Failed to get QR code for {instance.name}: {e}")
            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="whatsapp",
                status="error",
                message=f"Failed to get QR code: {str(e)}"
            )
    
    async def get_status(self, instance: InstanceConfig) -> ConnectionStatus:
        """Get WhatsApp connection status."""
        try:
            evolution_client = get_evolution_client()
            state_response = await evolution_client.get_connection_state(instance.name)
            
            # Map Evolution states to generic states
            evolution_state = state_response.get("instance", {}).get("state", "unknown")
            
            status_map = {
                "open": "connected",
                "close": "disconnected", 
                "connecting": "connecting",
                "unknown": "error"
            }
            
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="whatsapp",
                status=status_map.get(evolution_state, "error"),
                channel_data={
                    "evolution_state": evolution_state,
                    "evolution_data": state_response
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get status for {instance.name}: {e}")
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="whatsapp",
                status="error",
                channel_data={"error": str(e)}
            )
    
    async def restart_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Restart WhatsApp instance."""
        try:
            evolution_client = get_evolution_client()
            result = await evolution_client.restart_instance(instance.name)
            
            return {
                "status": "success",
                "message": f"WhatsApp instance '{instance.name}' restart initiated",
                "evolution_response": result
            }
            
        except Exception as e:
            logger.error(f"Failed to restart instance {instance.name}: {e}")
            raise Exception(f"WhatsApp instance restart failed: {str(e)}")
    
    async def logout_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Logout WhatsApp instance."""
        try:
            evolution_client = get_evolution_client()
            result = await evolution_client.logout_instance(instance.name)
            
            return {
                "status": "success",
                "message": f"WhatsApp instance '{instance.name}' logged out",
                "evolution_response": result
            }
            
        except Exception as e:
            logger.error(f"Failed to logout instance {instance.name}: {e}")
            raise Exception(f"WhatsApp instance logout failed: {str(e)}")
    
    async def delete_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Delete WhatsApp instance from Evolution API."""
        try:
            evolution_client = get_evolution_client()
            result = await evolution_client.delete_instance(instance.name)
            
            return {
                "status": "success",
                "message": f"WhatsApp instance '{instance.name}' deleted from Evolution API",
                "evolution_response": result
            }
            
        except Exception as e:
            logger.error(f"Failed to delete instance {instance.name}: {e}")
            # Don't raise exception - we still want to delete from database
            return {
                "status": "partial_success",
                "message": "Failed to delete from Evolution API but will remove from database",
                "error": str(e)
            }