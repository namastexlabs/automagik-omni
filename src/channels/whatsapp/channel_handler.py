"""
WhatsApp channel handler using Evolution API.
"""

import logging
from typing import Dict, Any
from src.channels.base import ChannelHandler, QRCodeResponse, ConnectionStatus
from src.channels.whatsapp.evolution_client import (
    EvolutionCreateRequest,
    EvolutionClient,
)
from src.db.models import InstanceConfig
from src.config import config
from src.ip_utils import replace_localhost_with_ipv4

logger = logging.getLogger(__name__)


class WhatsAppChannelHandler(ChannelHandler):
    """WhatsApp channel handler implementation."""

    def _get_evolution_client(self, instance: InstanceConfig) -> EvolutionClient:
        """Get Evolution client for this specific instance."""
        # Use instance-specific credentials if available, otherwise fall back to global
        evolution_url = instance.evolution_url or replace_localhost_with_ipv4(
            config.get_env("EVOLUTION_API_URL", "http://localhost:8080")
        )
        evolution_key = instance.evolution_key or config.get_env(
            "EVOLUTION_API_KEY", ""
        )

        logger.debug(
            f"Instance config - URL: {instance.evolution_url}, Key: {'*' * len(instance.evolution_key) if instance.evolution_key else 'NOT SET'}"
        )
        logger.debug(
            f"Final config - URL: {evolution_url}, Key: {'*' * len(evolution_key) if evolution_key else 'NOT SET'}"
        )

        # Validate configuration values
        if evolution_url.lower() in ["string", "null", "undefined", ""]:
            logger.error(
                f"Invalid Evolution URL detected: '{evolution_url}'. Please provide a valid URL like 'http://localhost:8080'"
            )
            raise Exception(
                f"Invalid Evolution URL: '{evolution_url}'. Please provide a valid URL like 'http://localhost:8080'"
            )

        if not evolution_key or evolution_key.lower() in [
            "string",
            "null",
            "undefined",
            "",
        ]:
            logger.error(
                f"Invalid Evolution API key detected: '{evolution_key}'. Please provide a valid API key."
            )
            raise Exception(
                f"Invalid Evolution API key: '{evolution_key}'. Please provide a valid API key."
            )

        if not evolution_url.startswith(("http://", "https://")):
            logger.error(
                f"Evolution URL missing protocol: '{evolution_url}'. Must start with http:// or https://"
            )
            raise Exception(
                f"Evolution URL missing protocol: '{evolution_url}'. Must start with http:// or https://"
            )

        logger.debug(
            f"Creating Evolution client for instance '{instance.name}' - URL: {evolution_url}"
        )
        logger.debug(
            f"Using Evolution API key: {evolution_key[:8]}{'*' * (len(evolution_key)-8) if len(evolution_key) > 8 else evolution_key}"
        )

        return EvolutionClient(evolution_url, evolution_key)

    async def create_instance(
        self, instance: InstanceConfig, **kwargs
    ) -> Dict[str, Any]:
        """Create a new WhatsApp instance in Evolution API or use existing one."""
        try:
            evolution_client = self._get_evolution_client(instance)

            # First, check if an Evolution instance with this name already exists
            logger.info(
                f"Checking if Evolution instance '{instance.name}' already exists..."
            )

            # Fetch all instances and filter locally to avoid 404 errors
            try:
                all_instances = await evolution_client.fetch_instances()
                existing_instances = [
                    inst for inst in all_instances if inst.instanceName == instance.name
                ]
            except Exception as fetch_error:
                logger.warning(f"Could not fetch existing instances: {fetch_error}")
                existing_instances = []

            if existing_instances:
                # Instance already exists, use it
                existing_instance = existing_instances[0]
                logger.info(
                    f"Evolution instance '{instance.name}' already exists, using existing instance"
                )

                # Set webhook URL for existing instance if needed
                webhook_url = replace_localhost_with_ipv4(
                    f"http://{config.api.host}:{config.api.port}/webhook/evolution/{instance.name}"
                )

                try:
                    await evolution_client.set_webhook(
                        instance.name,
                        webhook_url,
                        ["MESSAGES_UPSERT"],
                        instance.webhook_base64,
                    )
                    logger.info(
                        f"Updated webhook URL for existing instance: {webhook_url} (base64={instance.webhook_base64})"
                    )

                    # Also configure settings for existing instance
                    await evolution_client.set_settings(instance.name)
                    logger.info(
                        f"Updated settings for existing instance: {instance.name}"
                    )
                except Exception as config_error:
                    logger.warning(
                        f"Failed to update webhook/settings for existing instance: {config_error}"
                    )

                return {
                    "evolution_response": {
                        "instance": existing_instance.dict(),
                        "hash": {"apikey": existing_instance.apikey},
                    },
                    "evolution_instance_id": existing_instance.instanceId,
                    "evolution_apikey": existing_instance.apikey,
                    "webhook_url": webhook_url,
                    "existing_instance": True,
                }

            # Instance doesn't exist, create a new one
            logger.info(f"Creating new Evolution instance '{instance.name}'...")

            # Extract WhatsApp-specific parameters
            phone_number = kwargs.get("phone_number")
            auto_qr = kwargs.get("auto_qr", True)
            integration = kwargs.get("integration", "WHATSAPP-BAILEYS")

            # Set webhook URL automatically
            webhook_url = replace_localhost_with_ipv4(
                f"http://{config.api.host}:{config.api.port}/webhook/evolution/{instance.name}"
            )

            # Prepare Evolution API request (without webhook initially to avoid 403 errors)
            evolution_request = EvolutionCreateRequest(
                instanceName=instance.name,
                integration=integration,
                qrcode=auto_qr,
                number=phone_number,
            )

            response = await evolution_client.create_instance(evolution_request)
            logger.info(f"WhatsApp instance created: {response}")
            logger.debug(f"Response type: {type(response)}")

            # Note: Webhook is already configured during instance creation above
            # Additional settings configuration if needed
            try:
                await evolution_client.set_settings(instance.name)
                logger.info(
                    f"Configured additional settings for new instance: {instance.name}"
                )
            except Exception as config_error:
                logger.debug(
                    f"Additional settings configuration not needed or failed: {config_error}"
                )

            # Handle different response formats from Evolution API
            if isinstance(response, dict):
                evolution_instance_id = (
                    response.get("instance", {}).get("instanceId")
                    if isinstance(response.get("instance"), dict)
                    else None
                )
                evolution_apikey = (
                    response.get("hash", {}).get("apikey")
                    if isinstance(response.get("hash"), dict)
                    else response.get("hash")
                )
            else:
                logger.warning(
                    f"Unexpected response format from Evolution API: {response}"
                )
                evolution_instance_id = None
                evolution_apikey = None

            return {
                "evolution_response": response,
                "evolution_instance_id": evolution_instance_id,
                "evolution_apikey": evolution_apikey,
                "webhook_url": webhook_url,
                "existing_instance": False,
            }

        except Exception as e:
            logger.error(f"Failed to create WhatsApp instance: {e}")
            raise Exception(f"WhatsApp instance creation failed: {str(e)}")

    async def get_qr_code(self, instance: InstanceConfig) -> QRCodeResponse:
        """Get QR code for WhatsApp connection."""
        try:
            logger.debug(f"=== QR CODE REQUEST START for {instance.name} ===")
            logger.debug(f"Instance evolution_url: {instance.evolution_url}")
            logger.debug(
                f"Instance evolution_key: {instance.evolution_key[:8] if instance.evolution_key else 'None'}..."
            )

            evolution_client = self._get_evolution_client(instance)
            logger.debug("Evolution client created successfully")

            # First check the instance state
            logger.debug(f"Checking instance state before QR request: {instance.name}")
            state_response = await evolution_client.get_connection_state(instance.name)
            current_state = state_response.get("instance", {}).get("state", "unknown")
            logger.debug(f"Current instance state: {current_state}")

            # If instance is in connecting state, try to restart it first to get fresh QR
            if current_state == "connecting":
                logger.info(
                    "Instance is in connecting state, restarting to get fresh QR..."
                )
                try:
                    await evolution_client.restart_instance(instance.name)
                    logger.debug("Instance restart initiated")
                    # Wait a moment for restart to take effect
                    import asyncio

                    await asyncio.sleep(1)
                except Exception as restart_error:
                    logger.warning(f"Failed to restart instance: {restart_error}")
                    # Don't fail the QR code request if restart fails
                    # The instance might still be able to provide a QR code

            logger.debug(f"Calling Evolution API connect for instance: {instance.name}")
            connect_response = await evolution_client.connect_instance(instance.name)
            logger.debug(f"Evolution connect response type: {type(connect_response)}")
            logger.debug(f"Evolution connect response: {connect_response}")

            qr_code = None
            message = "QR code not available"

            # Extract QR code from response
            if isinstance(connect_response, dict):
                logger.debug(
                    f"Response is dict with keys: {list(connect_response.keys())}"
                )

                # Check for QR code in direct base64 field (Evolution API v2.x format)
                if "base64" in connect_response and connect_response["base64"]:
                    qr_code = connect_response["base64"]
                    logger.debug(
                        f"Found QR code in base64 field, length: {len(qr_code)}"
                    )
                    message = "QR code ready for scanning"
                # Check for QR code in nested qrcode object (older format)
                elif "qrcode" in connect_response:
                    qrcode_data = connect_response["qrcode"]
                    logger.debug(f"QRCode data type: {type(qrcode_data)}")
                    if isinstance(qrcode_data, dict) and "base64" in qrcode_data:
                        qr_code = qrcode_data.get("base64")
                        logger.debug(
                            f"Found QR code in nested format, length: {len(qr_code) if qr_code else 0}"
                        )
                        message = "QR code ready for scanning"
                    else:
                        logger.debug(f"QRCode data format unexpected: {qrcode_data}")
                elif "message" in connect_response:
                    message = connect_response["message"]
                    logger.debug(f"Connect response message: {message}")
                # Handle case where instance exists but no QR (like {"count": 0})
                elif "count" in connect_response and connect_response["count"] == 0:
                    message = "Instance exists but no QR available - may need to restart instance"
                    logger.debug("Got count=0 response, instance may need restart")
                else:
                    logger.debug(
                        "No base64, qrcode, message, or count field in response"
                    )
            else:
                logger.debug(f"Response is not dict: {connect_response}")

            logger.debug(f"Final QR code result: {'FOUND' if qr_code else 'NOT FOUND'}")
            logger.debug("=== QR CODE REQUEST END ===")

            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="whatsapp",
                qr_code=qr_code,
                status="success" if qr_code else "unavailable",
                message=message,
            )

        except Exception as e:
            logger.error(f"Failed to get QR code for {instance.name}: {e}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return QRCodeResponse(
                instance_name=instance.name,
                channel_type="whatsapp",
                status="error",
                message=f"Failed to get QR code: {str(e)}",
            )

    async def get_status(self, instance: InstanceConfig) -> ConnectionStatus:
        """Get WhatsApp connection status."""
        try:
            evolution_client = self._get_evolution_client(instance)
            state_response = await evolution_client.get_connection_state(instance.name)

            # Map Evolution states to generic states
            evolution_state = state_response.get("instance", {}).get("state", "unknown")

            status_map = {
                "open": "connected",
                "close": "disconnected",
                "connecting": "connecting",
                "unknown": "error",
            }

            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="whatsapp",
                status=status_map.get(evolution_state, "error"),
                channel_data={
                    "evolution_state": evolution_state,
                    "evolution_data": state_response,
                },
            )

        except Exception as e:
            logger.error(f"Failed to get status for {instance.name}: {e}")
            return ConnectionStatus(
                instance_name=instance.name,
                channel_type="whatsapp",
                status="error",
                channel_data={"error": str(e)},
            )

    async def restart_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Restart WhatsApp instance."""
        try:
            evolution_client = self._get_evolution_client(instance)
            result = await evolution_client.restart_instance(instance.name)

            return {
                "status": "success",
                "message": f"WhatsApp instance '{instance.name}' restart initiated",
                "evolution_response": result,
            }

        except Exception as e:
            logger.error(f"Failed to restart instance {instance.name}: {e}")
            raise Exception(f"WhatsApp instance restart failed: {str(e)}")

    async def logout_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Logout WhatsApp instance."""
        try:
            evolution_client = self._get_evolution_client(instance)
            result = await evolution_client.logout_instance(instance.name)

            return {
                "status": "success",
                "message": f"WhatsApp instance '{instance.name}' logged out",
                "evolution_response": result,
            }

        except Exception as e:
            logger.error(f"Failed to logout instance {instance.name}: {e}")
            raise Exception(f"WhatsApp instance logout failed: {str(e)}")

    async def delete_instance(self, instance: InstanceConfig) -> Dict[str, Any]:
        """Delete WhatsApp instance from Evolution API."""
        try:
            evolution_client = self._get_evolution_client(instance)
            result = await evolution_client.delete_instance(instance.name)

            return {
                "status": "success",
                "message": f"WhatsApp instance '{instance.name}' deleted from Evolution API",
                "evolution_response": result,
            }

        except Exception as e:
            logger.error(f"Failed to delete instance {instance.name}: {e}")
            # Don't raise exception - we still want to delete from database
            return {
                "status": "partial_success",
                "message": "Failed to delete from Evolution API but will remove from database",
                "error": str(e),
            }
