# 🚀 Automagik Omni API - Complete Developer Guide

*Generated on July 17, 2025 - Comprehensive API documentation with real examples*

## 📚 Table of Contents

1. [🏁 Quick Start](#-quick-start)
2. [🔐 Authentication](#-authentication)
3. [💪 Health & System](#-health--system)
4. [🏢 Instance Management](#-instance-management)
5. [⚡ Instance Operations](#-instance-operations)
6. [💬 Message Sending](#-message-sending)
7. [📊 Traces & Analytics](#-traces--analytics)
8. [🔗 Webhooks](#-webhooks)
9. [❌ Error Handling](#-error-handling)
10. [🔍 Filtering & Advanced Usage](#-filtering--advanced-usage)

---

## 🏁 Quick Start

### Base URL
```
http://localhost:18882
```

### Essential Headers
```bash
# Authentication (for protected endpoints)
-H "Authorization: Bearer namastex888"

# Content Type (for POST/PUT requests)
-H "Content-Type: application/json"
```

### Test the API
```bash
# Health check (no auth required)
curl http://localhost:18882/health

# List instances (auth required)
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances
```

---

## 🔐 Authentication

All API endpoints except `/health` and webhooks require authentication via Bearer token.

### Headers Required
```bash
Authorization: Bearer your_api_key_here
```

### Example
```bash
curl -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     http://localhost:18882/api/v1/instances
```

---

## 💪 Health & System

### Health Check
**No authentication required**

```bash
# Request
curl -X GET http://localhost:18882/health

# Response (200)
{
  "status": "healthy"
}
```

### Get Supported Channels
```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/supported-channels

# Response (200)
{
  "supported_channels": ["whatsapp"],
  "total_channels": 1
}
```

---

## 🏢 Instance Management

### List All Instances

#### Basic Listing
```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances

# Response (200) - Array of instances
[
  {
    "id": 1,
    "name": "my-whatsapp-instance",
    "channel_type": "whatsapp",
    "evolution_url": "http://172.19.209.168:18080",
    "evolution_key": "09A08CCA-C644-4555-83C2-D866348F5B68",
    "whatsapp_instance": "my-whatsapp-instance",
    "session_id_prefix": "automagik_",
    "webhook_base64": true,
    "agent_api_url": "http://172.19.209.168:18881",
    "agent_api_key": "namastex888",
    "default_agent": "discord",
    "agent_timeout": 60,
    "is_default": true,
    "is_active": false,
    "automagik_instance_id": "automagik-1752087186026-k28555wiq",
    "automagik_instance_name": "AutomagikAPI Local",
    "created_at": "2025-07-09T21:29:31.274476",
    "updated_at": "2025-07-17T20:35:36.302314",
    "evolution_status": {
      "state": "connecting",
      "owner_jid": null,
      "profile_name": null,
      "profile_picture_url": null,
      "last_updated": "2025-07-17T17:47:51.635032",
      "error": null
    }
  }
]
```

#### With Pagination and Options
```bash
# Request with pagination and status
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/instances?skip=0&limit=5&include_status=true"

# Without Evolution status (faster)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/instances?include_status=false"
```

### Get Specific Instance
```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-whatsapp-instance

# Response (200) - Single instance object
{
  "id": 1,
  "name": "my-whatsapp-instance",
  "channel_type": "whatsapp",
  // ... same fields as above
}

# Response (404) - Instance not found
{
  "detail": "Instance 'nonexistent-instance' not found"
}
```

### Create New Instance
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "new-instance",
       "channel_type": "whatsapp",
       "evolution_url": "http://172.19.209.168:18080",
       "evolution_key": "your-evolution-api-key",
       "agent_api_url": "http://172.19.209.168:18881",
       "agent_api_key": "namastex888",
       "default_agent": "my-agent",
       "webhook_base64": false,
       "phone_number": "+5511999999999"
     }' \
     http://localhost:18882/api/v1/instances

# Response (201) - Created successfully
{
  "id": 3,
  "name": "new-instance",
  "channel_type": "whatsapp",
  "is_active": true,
  // ... full instance object
}

# Response (400) - Instance already exists
{
  "detail": "Instance 'new-instance' already exists"
}

# Response (422) - Validation error
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required"
    }
  ]
}
```

#### Required Fields for Instance Creation
- `name`: Unique instance identifier
- `channel_type`: Currently only "whatsapp"
- `evolution_url`: WhatsApp Evolution API URL
- `evolution_key`: Evolution API authentication key
- `agent_api_url`: Your agent/AI service URL
- `agent_api_key`: Agent service authentication key
- `default_agent`: Default agent to use

#### Optional Fields
- `webhook_base64`: Send base64 encoded media (default: true)
- `phone_number`: WhatsApp phone number
- `auto_qr`: Auto-generate QR code (default: true)
- `integration`: WhatsApp integration type (default: "WHATSAPP-BAILEYS")
- `agent_timeout`: Timeout in seconds (default: 60)
- `is_default`: Set as default instance (default: false)

### Update Instance
```bash
# Request
curl -X PUT \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "agent_api_url": "https://updated-agent.example.com",
       "webhook_base64": true,
       "default_agent": "updated-agent"
     }' \
     http://localhost:18882/api/v1/instances/my-instance

# Response (200) - Updated instance object
{
  "id": 1,
  "name": "my-instance",
  "agent_api_url": "https://updated-agent.example.com",
  "webhook_base64": true,
  "default_agent": "updated-agent",
  // ... other fields
}
```

### Delete Instance
```bash
# Request
curl -X DELETE \
     -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-instance

# Response (204) - Deleted successfully (no content)

# Response (400) - Cannot delete only remaining instance
{
  "detail": "Cannot delete the only remaining instance"
}

# Response (404) - Instance not found
{
  "detail": "Instance 'nonexistent-instance' not found"
}
```

---

## ⚡ Instance Operations

### Get QR Code for WhatsApp Connection
```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-instance/qr

# Response (200) - QR code available
{
  "instance_name": "my-instance",
  "channel_type": "whatsapp",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA...",
  "auth_url": null,
  "invite_url": null,
  "status": "success",
  "message": "QR code ready for scanning"
}

# Response (200) - QR code not available
{
  "instance_name": "my-instance",
  "channel_type": "whatsapp",
  "qr_code": null,
  "status": "unavailable",
  "message": "Instance exists but no QR available - may need to restart instance"
}
```

### Get Instance Connection Status
```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-instance/status

# Response (200) - Connected
{
  "instance_name": "my-instance",
  "channel_type": "whatsapp",
  "status": "connected",
  "channel_data": {
    "evolution_state": "open",
    "evolution_data": {
      "instance": {
        "state": "open",
        "ownerJid": "5511999999999@s.whatsapp.net",
        "profileName": "My Profile",
        "profilePictureUrl": "https://example.com/profile.jpg"
      }
    }
  }
}

# Response (200) - Disconnected
{
  "instance_name": "my-instance",
  "channel_type": "whatsapp",
  "status": "disconnected",
  "channel_data": {
    "evolution_state": "close"
  }
}
```

### Set Instance as Default
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-instance/set-default

# Response (200) - Instance now set as default
{
  "id": 1,
  "name": "my-instance",
  "is_default": true,
  // ... other fields
}
```

### Restart Instance Connection
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-instance/restart

# Response (200)
{
  "status": "success",
  "message": "WhatsApp instance 'my-instance' restart initiated",
  "evolution_response": { /* Evolution API response */ }
}
```

### Logout Instance
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/my-instance/logout

# Response (200)
{
  "status": "success",
  "message": "WhatsApp instance 'my-instance' logged out",
  "evolution_response": { /* Evolution API response */ }
}
```

### Discover Evolution Instances
*Auto-discovers instances from Evolution API and creates missing database entries*

```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/discover

# Response (200) - Instances found
{
  "status": "success",
  "message": "Discovered 2 Evolution instances",
  "instances": [
    {
      "name": "discovered-instance-1",
      "active": true,
      "agent_id": "agent-123"
    },
    {
      "name": "discovered-instance-2", 
      "active": false,
      "agent_id": "agent-456"
    }
  ]
}

# Response (200) - No new instances
{
  "status": "success",
  "message": "No new Evolution instances discovered",
  "instances": []
}
```

---

## 💬 Message Sending

All message endpoints require an active WhatsApp instance.

### Send Text Message
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+5511999999999",
       "text": "Hello! This is a test message from the API."
     }' \
     http://localhost:18882/api/v1/instance/my-instance/send-text

# Response (200)
{
  "success": true,
  "message_id": "msg_12345",
  "timestamp": 1642789200
}

# Response (404) - Instance not found
{
  "detail": "Instance 'nonexistent-instance' not found"
}
```

### Send Media Message
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+5511999999999",
       "media_url": "https://example.com/image.jpg",
       "caption": "Check out this image!",
       "media_type": "image"
     }' \
     http://localhost:18882/api/v1/instance/my-instance/send-media

# Response (200)
{
  "success": true,
  "message_id": "msg_12346",
  "timestamp": 1642789220
}
```

#### Supported Media Types
- `image`: JPG, PNG, GIF
- `video`: MP4, AVI, MOV
- `document`: PDF, DOC, XLS, etc.
- `audio`: MP3, WAV, OGG

### Send Audio Message
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+5511999999999",
       "audio_url": "https://example.com/audio.mp3",
       "caption": "Voice message"
     }' \
     http://localhost:18882/api/v1/instance/my-instance/send-audio

# Response (200)
{
  "success": true,
  "message_id": "msg_12347"
}
```

### Send Contact
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+5511999999999",
       "contact": {
         "name": "John Doe",
         "phone": "+5511888888888"
       }
     }' \
     http://localhost:18882/api/v1/instance/my-instance/send-contact

# Response (200)
{
  "success": true,
  "message_id": "msg_12348"
}
```

### Send Reaction
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+5511999999999",
       "message_id": "original_message_id",
       "emoji": "👍"
     }' \
     http://localhost:18882/api/v1/instance/my-instance/send-reaction

# Response (200)
{
  "success": true,
  "message_id": "reaction_msg_12349"
}
```

### Fetch WhatsApp Profile
```bash
# Request
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "phone_number": "+5511999999999"
     }' \
     http://localhost:18882/api/v1/instance/my-instance/fetch-profile

# Response (200)
{
  "success": true,
  "profile": {
    "name": "John Doe",
    "about": "Hey there! I am using WhatsApp.",
    "picture_url": "https://example.com/profile.jpg"
  }
}
```

---

## 📊 Traces & Analytics

### List Message Traces

#### Basic Listing
```bash
# Request - All traces
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/traces

# Response (200)
[
  {
    "trace_id": "26e2a090-f9f1-4ff4-bfcc-74303c577fbf",
    "instance_name": "my-instance",
    "whatsapp_message_id": "3EB0A3415526509D93C2A4",
    "sender_phone": "555197285829",
    "sender_name": "John Doe",
    "message_type": "text",
    "has_media": false,
    "has_quoted_message": false,
    "session_name": null,
    "agent_session_id": "e8433c84-b39c-4197-82e8-c6e924c19fe6",
    "status": "completed",
    "error_message": null,
    "error_stage": null,
    "received_at": "2025-07-08T20:15:23.195094",
    "completed_at": "2025-07-08T20:15:25.053935",
    "agent_processing_time_ms": 1489,
    "total_processing_time_ms": 1858,
    "agent_response_success": true,
    "evolution_success": true
  }
]
```

#### With Filters
```bash
# Completed messages only
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?status=completed&limit=10"

# Specific instance
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?instance_name=my-instance"

# By message type
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?message_type=audio&has_media=true"

# Date range
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?start_date=2025-07-01&end_date=2025-07-31"

# Specific sender
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?sender_phone=5511999999999"
```

### Get Specific Trace
```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/traces/26e2a090-f9f1-4ff4-bfcc-74303c577fbf

# Response (200) - Detailed trace information
{
  "trace_id": "26e2a090-f9f1-4ff4-bfcc-74303c577fbf",
  "instance_name": "my-instance",
  "whatsapp_message_id": "3EB0A3415526509D93C2A4",
  "sender_phone": "555197285829",
  "sender_name": "John Doe",
  "message_type": "text",
  "has_media": false,
  "status": "completed",
  "received_at": "2025-07-08T20:15:23.195094",
  "completed_at": "2025-07-08T20:15:25.053935",
  "agent_processing_time_ms": 1489,
  "total_processing_time_ms": 1858,
  "agent_response_success": true,
  "evolution_success": true
}

# Response (404) - Trace not found
{
  "detail": "Trace 'invalid-trace-id' not found"
}
```

### Get Trace Payloads
*Detailed payload information for debugging*

```bash
# Request
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/traces/26e2a090-f9f1-4ff4-bfcc-74303c577fbf/payloads

# Response (200)
[
  {
    "id": 1,
    "trace_id": "26e2a090-f9f1-4ff4-bfcc-74303c577fbf",
    "stage": "webhook_received",
    "payload_type": "webhook_data",
    "timestamp": "2025-07-08T20:15:23.195094",
    "size_bytes": 1024,
    "contains_media": false,
    "contains_base64": false,
    "payload": {
      "event": "messages.upsert",
      "data": {
        "messages": [/* WhatsApp message data */]
      }
    }
  },
  {
    "id": 2,
    "trace_id": "26e2a090-f9f1-4ff4-bfcc-74303c577fbf",
    "stage": "agent_response",
    "payload_type": "agent_response",
    "timestamp": "2025-07-08T20:15:24.684187",
    "size_bytes": 512,
    "contains_media": false,
    "contains_base64": false,
    "payload": {
      "response": "Hello! How can I help you today?",
      "success": true
    }
  }
]
```

### Analytics Summary
```bash
# Request - Default (last 24 hours)
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/analytics/summary

# Request - Custom date range
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/analytics/summary?start_date=2025-07-01&end_date=2025-07-31"

# Response (200)
{
  "total_messages": 156,
  "completed_messages": 142,
  "failed_messages": 14,
  "success_rate": 91.03,
  "avg_processing_time_ms": 2341,
  "message_types": {
    "text": 120,
    "audio": 20,
    "image": 16
  },
  "instances": {
    "my-instance": 89,
    "another-instance": 67
  },
  "hourly_distribution": [
    {"hour": 0, "count": 2},
    {"hour": 1, "count": 1},
    // ... 24 hours
  ]
}
```

---

## 🔗 Webhooks

Webhooks allow Evolution API to send incoming messages to your Automagik Omni instance.

### Instance-Specific Webhooks (Recommended)
```bash
# URL Format
POST http://localhost:18882/webhook/evolution/{instance_name}

# Example webhook from Evolution API
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "event": "messages.upsert",
       "data": {
         "messages": [{
           "key": {
             "remoteJid": "5511999999999@s.whatsapp.net",
             "id": "3EB0A3415526509D93C2A4"
           },
           "message": {
             "conversation": "Hello! I need help with my order."
           },
           "messageTimestamp": 1642789200
         }]
       },
       "instance": "my-instance"
     }' \
     http://localhost:18882/webhook/evolution/my-instance

# Response (200) - Message processed
{
  "status": "success",
  "instance": "my-instance",
  "trace_id": "77feecc7-19aa-475f-b974-26d4429dd604"
}
```

### Default Webhook (Backward Compatibility)
```bash
# URL for default instance
POST http://localhost:18882/webhook/evolution

# Example
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{
       "event": "messages.upsert",
       "data": {
         "messages": [{
           "key": {
             "remoteJid": "5511999999999@s.whatsapp.net",
             "id": "3EB0A3415526509D93C2A4"
           },
           "message": {
             "conversation": "Hello!"
           }
         }]
       }
     }' \
     http://localhost:18882/webhook/evolution

# Response (200)
{
  "status": "success",
  "instance": "default-instance-name",
  "trace_id": "uuid-here"
}
```

### Webhook Configuration in Evolution API
When creating instances, webhooks are automatically configured. You can also set them manually:

```json
{
  "enabled": true,
  "url": "http://your-server:18882/webhook/evolution/my-instance",
  "events": ["MESSAGES_UPSERT"],
  "base64": false
}
```

---

## ❌ Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Request successful |
| 201 | Created | Instance created |
| 204 | No Content | Instance deleted |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing/invalid API key |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server error |

### Error Response Formats

#### Simple Error
```json
{
  "detail": "Instance 'nonexistent' not found"
}
```

#### Validation Error (422)
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "name"],
      "msg": "Field required",
      "input": {},
      "url": "https://errors.pydantic.dev/2.0/v/missing"
    },
    {
      "type": "string_too_short",
      "loc": ["body", "phone_number"],
      "msg": "String should have at least 10 characters",
      "input": "+123",
      "ctx": {"min_length": 10}
    }
  ]
}
```

### Common Error Scenarios

#### Authentication Errors
```bash
# Missing Authorization header
curl http://localhost:18882/api/v1/instances
# Response (401): {"detail": "Not authenticated"}

# Invalid API key
curl -H "Authorization: Bearer invalid-key" \
     http://localhost:18882/api/v1/instances
# Response (401): {"detail": "Invalid API key"}
```

#### Validation Errors
```bash
# Empty required field
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{"name": ""}' \
     http://localhost:18882/api/v1/instances
# Response (422): Validation error details
```

#### Resource Not Found
```bash
# Nonexistent instance
curl -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances/does-not-exist
# Response (404): {"detail": "Instance 'does-not-exist' not found"}
```

#### Evolution API Errors
```bash
# Invalid Evolution API credentials
curl -X POST \
     -H "Authorization: Bearer namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "test-instance",
       "channel_type": "whatsapp",
       "evolution_url": "http://invalid-url",
       "evolution_key": "invalid-key",
       "agent_api_url": "http://agent",
       "agent_api_key": "key",
       "default_agent": "agent"
     }' \
     http://localhost:18882/api/v1/instances
# Response (500): {"detail": "Failed to create whatsapp instance: Evolution API error: 401 - Unauthorized"}
```

---

## 🔍 Filtering & Advanced Usage

### Query Parameters

#### Instance Listing
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Records to skip (pagination) |
| `limit` | integer | 100 | Max records to return |
| `include_status` | boolean | true | Include Evolution API status |

#### Trace Filtering
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | integer | 0 | Records to skip |
| `limit` | integer | 100 | Max records to return |
| `status` | string | - | Filter by status: `completed`, `processing`, `failed` |
| `instance_name` | string | - | Filter by specific instance |
| `message_type` | string | - | Filter by type: `text`, `audio`, `image`, `video`, `document` |
| `session_name` | string | - | Filter by session name (human-readable session identifier) |
| `agent_session_id` | string | - | Filter by agent session ID (from agent API response) |
| `start_date` | string | - | Start date (ISO format): `2025-07-01` |
| `end_date` | string | - | End date (ISO format): `2025-07-31` |
| `sender_phone` | string | - | Filter by sender phone (digits only) |
| `phone` | string | - | Filter by sender phone (alias for sender_phone) |
| `has_media` | boolean | - | Filter by media presence |
| `has_quoted_message` | boolean | - | Filter by quoted messages |

### Advanced Query Examples

#### Pagination
```bash
# First page (0-19)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?skip=0&limit=20"

# Second page (20-39)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?skip=20&limit=20"
```

#### Complex Filtering
```bash
# Failed messages in the last week
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?status=failed&start_date=2025-07-10&end_date=2025-07-17"

# Media messages from specific sender
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?sender_phone=5511999999999&has_media=true"

# Audio messages for specific instance
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?instance_name=my-instance&message_type=audio"

# Recent completed messages (last 50)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?status=completed&limit=50" | jq '.[0:10]'
```

#### Session-Based Filtering
```bash
# All messages for a specific agent session
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?agent_session_id=session_abc123"

# All messages for a specific session name (human-readable)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?session_name=user_john_conversation"

# Combine session and status filtering
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?session_name=user_john_conversation&status=completed"

# Find all sessions for a user (by phone)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?sender_phone=5511999999999" | \
     jq '[.[] | {trace_id, session_name, agent_session_id, message_type}]'
```

#### Performance Optimization
```bash
# Fast instance listing (no Evolution status)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/instances?include_status=false"

# Light trace listing (smaller limit)
curl -H "Authorization: Bearer namastex888" \
     "http://localhost:18882/api/v1/traces?limit=10"
```

### Response Parsing with jq

#### Extract Specific Fields
```bash
# Get only instance names
curl -s -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances | jq '.[].name'

# Get trace IDs and statuses
curl -s -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/traces | jq '.[] | {trace_id, status}'

# Get instances with their connection states
curl -s -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances | jq '.[] | {name, evolution_status: .evolution_status.state}'
```

#### Filtering Results
```bash
# Only connected instances
curl -s -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/instances | jq '.[] | select(.evolution_status.state == "open")'

# Only failed traces
curl -s -H "Authorization: Bearer namastex888" \
     http://localhost:18882/api/v1/traces | jq '.[] | select(.status == "failed")'
```

### Batch Operations Example Script

```bash
#!/bin/bash
# Example: Check all instances and their status

API_KEY="namastex888"
BASE_URL="http://localhost:18882"

echo "=== Instance Status Report ==="

# Get all instances
instances=$(curl -s -H "Authorization: Bearer $API_KEY" \
            "$BASE_URL/api/v1/instances" | jq -r '.[].name')

for instance in $instances; do
    echo "Instance: $instance"
    
    # Get status
    status=$(curl -s -H "Authorization: Bearer $API_KEY" \
             "$BASE_URL/api/v1/instances/$instance/status" | jq -r '.status')
    echo "  Status: $status"
    
    # Get recent traces count
    traces=$(curl -s -H "Authorization: Bearer $API_KEY" \
             "$BASE_URL/api/v1/traces?instance_name=$instance&limit=1" | jq '. | length')
    echo "  Recent traces: $traces"
    
    echo "---"
done
```

---

## 📱 Frontend Integration Examples

### JavaScript/TypeScript
```javascript
class AutomagikAPI {
  constructor(baseURL = 'http://localhost:18882', apiKey = 'namastex888') {
    this.baseURL = baseURL;
    this.apiKey = apiKey;
  }

  async request(method, endpoint, data = null) {
    const config = {
      method,
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      }
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, config);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Instance methods
  async listInstances() {
    return this.request('GET', '/api/v1/instances');
  }

  async createInstance(instanceData) {
    return this.request('POST', '/api/v1/instances', instanceData);
  }

  async getInstance(name) {
    return this.request('GET', `/api/v1/instances/${name}`);
  }

  async getQRCode(instanceName) {
    return this.request('GET', `/api/v1/instances/${instanceName}/qr`);
  }

  // Message methods
  async sendText(instanceName, phoneNumber, text) {
    return this.request('POST', `/api/v1/instance/${instanceName}/send-text`, {
      phone_number: phoneNumber,
      text: text
    });
  }

  async sendMedia(instanceName, phoneNumber, mediaUrl, caption, mediaType) {
    return this.request('POST', `/api/v1/instance/${instanceName}/send-media`, {
      phone_number: phoneNumber,
      media_url: mediaUrl,
      caption: caption,
      media_type: mediaType
    });
  }

  // Trace methods
  async getTraces(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.request('GET', `/api/v1/traces?${params}`);
  }

  async getTrace(traceId) {
    return this.request('GET', `/api/v1/traces/${traceId}`);
  }
}

// Usage example
const api = new AutomagikAPI();

// List all instances
const instances = await api.listInstances();
console.log('Instances:', instances);

// Send a message
const result = await api.sendText('my-instance', '+5511999999999', 'Hello!');
console.log('Message sent:', result);

// Get recent traces
const traces = await api.getTraces({ limit: 10, status: 'completed' });
console.log('Recent traces:', traces);
```

### Python
```python
import requests
import json

class AutomagikAPI:
    def __init__(self, base_url="http://localhost:18882", api_key="namastex888"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    # Instance methods
    def list_instances(self):
        return self.request('GET', '/api/v1/instances')

    def create_instance(self, instance_data):
        return self.request('POST', '/api/v1/instances', instance_data)

    def get_instance(self, name):
        return self.request('GET', f'/api/v1/instances/{name}')

    def get_qr_code(self, instance_name):
        return self.request('GET', f'/api/v1/instances/{instance_name}/qr')

    # Message methods
    def send_text(self, instance_name, phone_number, text):
        return self.request('POST', f'/api/v1/instance/{instance_name}/send-text', {
            'phone_number': phone_number,
            'text': text
        })

    def send_media(self, instance_name, phone_number, media_url, caption, media_type):
        return self.request('POST', f'/api/v1/instance/{instance_name}/send-media', {
            'phone_number': phone_number,
            'media_url': media_url,
            'caption': caption,
            'media_type': media_type
        })

    # Trace methods
    def get_traces(self, **filters):
        params = '&'.join([f'{k}={v}' for k, v in filters.items()])
        endpoint = f'/api/v1/traces?{params}' if params else '/api/v1/traces'
        return self.request('GET', endpoint)

    def get_trace(self, trace_id):
        return self.request('GET', f'/api/v1/traces/{trace_id}')

# Usage example
api = AutomagikAPI()

# List instances
instances = api.list_instances()
print(f"Found {len(instances)} instances")

# Send message
result = api.send_text('my-instance', '+5511999999999', 'Hello from Python!')
print(f"Message sent: {result}")

# Get traces
traces = api.get_traces(limit=5, status='completed')
print(f"Recent traces: {len(traces)}")
```

---

*This comprehensive guide covers all Automagik Omni API endpoints with real examples, error handling, and integration patterns. For the latest updates, refer to the interactive API documentation at `http://localhost:18882/api/v1/docs`.*