"""
Real sample data for testing based on actual database traces.
This file contains realistic webhook payloads and API responses.
"""

# Real WhatsApp webhook payload samples (based on actual Evolution API data)
SAMPLE_WEBHOOK_PAYLOAD = {
    "event": "messages.upsert",
    "data": {
        "messages": [
            {
                "key": {"remoteJid": "555197285829@s.whatsapp.net", "id": "msg_12345_test", "fromMe": False},
                "message": {"conversation": "Hello! This is a test message."},
                "messageTimestamp": 1720372139,
                "pushName": "Test User",
                "status": "received",
            }
        ]
    },
    "instance": "test-instance",
}

SAMPLE_IMAGE_WEBHOOK_PAYLOAD = {
    "event": "messages.upsert",
    "data": {
        "messages": [
            {
                "key": {"remoteJid": "555197285829@s.whatsapp.net", "id": "msg_image_test", "fromMe": False},
                "message": {
                    "imageMessage": {
                        "url": "https://example.com/image.jpg",
                        "mimetype": "image/jpeg",
                        "caption": "Test image caption",
                        "fileLength": 45678,
                    }
                },
                "messageTimestamp": 1720372200,
                "pushName": "Test User",
            }
        ]
    },
    "instance": "test-instance",
}

# Real Evolution API responses (based on actual API behavior)
SAMPLE_EVOLUTION_QR_RESPONSE = {
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABLAAAASwAQAAAABs8+tMAAA...",
    "status": "qr_code",
    "instance": "test-instance",
}

SAMPLE_EVOLUTION_STATUS_RESPONSE = {
    "status": "connected",
    "connection": "open",
    "user": {
        "id": "555197285829@s.whatsapp.net",
        "name": "Test User",
        "profilePictureUrl": "https://example.com/profile.jpg",
    },
    "instance": "test-instance",
}

SAMPLE_EVOLUTION_SEND_RESPONSE = {
    "success": True,
    "message_id": "msg_sent_12345",
    "timestamp": 1720372300,
    "status": "sent",
}

# Real Agent API responses (based on actual agent service behavior)
SAMPLE_AGENT_RESPONSE = {
    "success": True,
    "agent_response": "Thank you for your message! How can I help you today?",
    "session_id": "session_12345",
    "user_id": "user_67890",
    "tokens_used": 45,
    "processing_time_ms": 1250,
    "tools_used": [],
}

SAMPLE_AGENT_ERROR_RESPONSE = {
    "success": False,
    "error": "Agent service temporarily unavailable",
    "error_code": "SERVICE_UNAVAILABLE",
    "retry_after": 30,
}

# Real instance configurations (based on actual database data)
SAMPLE_INSTANCE_CONFIG = {
    "name": "test-instance",
    "channel_type": "whatsapp",
    "whatsapp_instance": "test-whatsapp-123",
    "evolution_url": "http://172.19.209.168:18080",
    "evolution_key": "real-evolution-key-123",
    "agent_api_url": "http://172.19.209.168:18881",
    "agent_api_key": "real-agent-key-123",
    "default_agent": "test-agent",
    "webhook_base64": True,
    "is_default": True,
    "is_active": True,
}

# Trace data samples (based on actual message_traces table)
SAMPLE_TRACE_DATA = {
    "trace_id": "2b7e491c-4e81-475d-8f73-cdeb2d2ae17f",
    "instance_name": "test-instance",
    "whatsapp_message_id": "msg_12345_test",
    "sender_phone": "555197285829",
    "sender_name": "Test User",
    "sender_jid": "555197285829@s.whatsapp.net",
    "message_type": "text",
    "has_media": False,
    "has_quoted_message": False,
    "message_length": 25,
    "session_name": "session_test_123",
    "status": "completed",
    "agent_processing_time_ms": 1250,
    "total_processing_time_ms": 2100,
    "agent_request_tokens": 15,
    "agent_response_tokens": 30,
    "agent_response_success": True,
    "evolution_response_code": 200,
    "evolution_success": True,
}

# Phone number samples (realistic formats)
SAMPLE_PHONE_NUMBERS = ["+555197285829", "+1234567890", "+447911123456", "+33612345678", "+5511987654321"]

# Error scenarios with realistic error messages
SAMPLE_ERROR_RESPONSES = {
    "evolution_connection_error": {
        "error": "Failed to connect to Evolution API",
        "details": "Connection timeout after 30 seconds",
        "code": "CONNECTION_TIMEOUT",
    },
    "agent_api_error": {
        "error": "Agent API returned error",
        "details": "Rate limit exceeded",
        "code": "RATE_LIMIT_EXCEEDED",
    },
    "instance_not_found": {
        "error": "Instance not found",
        "details": "No instance found with name 'nonexistent'",
        "code": "INSTANCE_NOT_FOUND",
    },
}
