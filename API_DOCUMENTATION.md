# Omni-Hub API Documentation

## Overview

Omni-Hub is a multi-tenant messaging API that supports WhatsApp, Slack, and Discord channels. It provides comprehensive instance management and webhook processing capabilities.

**Base URL**: `http://localhost:8000` (development)  
**API Prefix**: `/api/v1`  
**Documentation**: `/api/v1/docs` (Swagger UI)

## Authentication

All API endpoints (except health and webhooks) require Bearer token authentication.

**Header**: `Authorization: Bearer <your_api_key>`

- If no API key is configured in development, all requests are allowed
- Production environments require proper API key configuration

## Endpoints

### Health Check

#### GET /health
Basic health check endpoint (no authentication required).

**Response**:
```json
{
  "status": "healthy"
}
```

---

### Webhook Endpoints

*Note: These endpoints do not require authentication as they're called by external services.*

#### POST /webhook/evolution
Default webhook for backward compatibility. Uses default instance configuration.

**Request Body**: Evolution API webhook payload (JSON)

**Response**:
```json
{
  "status": "success",
  "instance": "default_instance_name"
}
```

#### POST /webhook/evolution/{instance_name}
Multi-tenant webhook for specific instances.

**Path Parameters**:
- `instance_name` (string): Name of the target instance

**Request Body**: Evolution API webhook payload (JSON)

**Response**:
```json
{
  "status": "success", 
  "instance": "instance_name"
}
```

---

### Instance Management

#### GET /api/v1/instances/supported-channels
Get list of supported channel types.

**Authentication**: Required

**Response**:
```json
{
  "supported_channels": ["whatsapp", "slack", "discord"],
  "total_channels": 3
}
```

#### POST /api/v1/instances
Create a new instance configuration.

**Authentication**: Required

**Request Body**:
```json
{
  "name": "my_instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "your_evolution_api_key",
  "whatsapp_instance": "my_instance",
  "session_id_prefix": "my_instance-",
  "phone_number": "+1234567890",
  "auto_qr": true,
  "integration": "WHATSAPP-BAILEYS",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "your_agent_api_key",
  "default_agent": "default",
  "agent_timeout": 60,
  "is_default": false
}
```

**Request Schema**:
- `name` (string, required): Unique instance name
- `channel_type` (string, default: "whatsapp"): Channel type (whatsapp, slack, discord)
- `evolution_url` (string, optional): Evolution API URL for WhatsApp
- `evolution_key` (string, optional): Evolution API key for WhatsApp
- `whatsapp_instance` (string, optional): WhatsApp instance name
- `session_id_prefix` (string, optional): Session ID prefix for WhatsApp
- `phone_number` (string, optional): Phone number for WhatsApp (creation only)
- `auto_qr` (boolean, default: true): Auto-generate QR code for WhatsApp
- `integration` (string, default: "WHATSAPP-BAILEYS"): WhatsApp integration type
- `agent_api_url` (string, required): Agent service URL
- `agent_api_key` (string, required): Agent service API key
- `default_agent` (string, required): Default agent name
- `agent_timeout` (integer, default: 60): Agent timeout in seconds
- `is_default` (boolean, default: false): Set as default instance

**Response** (201 Created):
```json
{
  "id": 1,
  "name": "my_instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "your_evolution_api_key",
  "whatsapp_instance": "my_instance",
  "session_id_prefix": "my_instance-",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "your_agent_api_key",
  "default_agent": "default",
  "agent_timeout": 60,
  "is_default": false,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z"
}
```

#### GET /api/v1/instances
List all instance configurations.

**Authentication**: Required

**Query Parameters**:
- `skip` (integer, default: 0): Number of records to skip
- `limit` (integer, default: 100): Maximum number of records to return

**Response**:
```json
[
  {
    "id": 1,
    "name": "instance1",
    "channel_type": "whatsapp",
    "evolution_url": "http://localhost:8080",
    "evolution_key": "key1",
    "whatsapp_instance": "instance1",
    "session_id_prefix": "instance1-",
    "agent_api_url": "http://localhost:3000",
    "agent_api_key": "agent_key1",
    "default_agent": "default",
    "agent_timeout": 60,
    "is_default": true,
    "created_at": "2023-12-01T10:00:00Z",
    "updated_at": "2023-12-01T10:00:00Z"
  }
]
```

#### GET /api/v1/instances/{instance_name}
Get a specific instance configuration.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "id": 1,
  "name": "my_instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "your_evolution_api_key",
  "whatsapp_instance": "my_instance",
  "session_id_prefix": "my_instance-",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "your_agent_api_key",
  "default_agent": "default",
  "agent_timeout": 60,
  "is_default": false,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Instance not found

#### PUT /api/v1/instances/{instance_name}
Update an instance configuration.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Request Body** (all fields optional):
```json
{
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "new_evolution_key",
  "whatsapp_instance": "updated_instance",
  "session_id_prefix": "updated-",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "new_agent_key",
  "default_agent": "updated_agent",
  "agent_timeout": 120,
  "is_default": true
}
```

**Response**:
```json
{
  "id": 1,
  "name": "my_instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "new_evolution_key",
  "whatsapp_instance": "updated_instance",
  "session_id_prefix": "updated-",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "new_agent_key",
  "default_agent": "updated_agent",
  "agent_timeout": 120,
  "is_default": true,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:30:00Z"
}
```

#### DELETE /api/v1/instances/{instance_name}
Delete an instance configuration.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**: 204 No Content

**Error Responses**:
- `404 Not Found`: Instance not found
- `400 Bad Request`: Cannot delete the only remaining instance

#### GET /api/v1/instances/{instance_name}/default
Get the default instance configuration.

**Authentication**: Required

**Response**:
```json
{
  "id": 1,
  "name": "default_instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "default_key",
  "whatsapp_instance": "default_instance",
  "session_id_prefix": "default-",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "default_agent_key",
  "default_agent": "default",
  "agent_timeout": 60,
  "is_default": true,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:00Z"
}
```

#### POST /api/v1/instances/{instance_name}/set-default
Set an instance as the default.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "id": 1,
  "name": "my_instance",
  "channel_type": "whatsapp",
  "evolution_url": "http://localhost:8080",
  "evolution_key": "your_evolution_api_key",
  "whatsapp_instance": "my_instance",
  "session_id_prefix": "my_instance-",
  "agent_api_url": "http://localhost:3000",
  "agent_api_key": "your_agent_api_key",
  "default_agent": "default",
  "agent_timeout": 60,
  "is_default": true,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:30:00Z"
}
```

---

### Channel Operations

#### GET /api/v1/instances/{instance_name}/qr
Get QR code or connection info for any channel type.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "instance_name": "my_instance",
  "channel_type": "whatsapp",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "auth_url": null,
  "invite_url": null,
  "status": "waiting_for_scan",
  "message": "QR code generated successfully"
}
```

**Response Schema**:
- `instance_name` (string): Instance name
- `channel_type` (string): Channel type
- `qr_code` (string, optional): Base64 encoded QR code (WhatsApp)
- `auth_url` (string, optional): OAuth URL (Slack)
- `invite_url` (string, optional): Invite URL (Discord)
- `status` (string): Connection status
- `message` (string): Status message

#### GET /api/v1/instances/{instance_name}/status
Get connection status for any channel type.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "instance_name": "my_instance",
  "channel_type": "whatsapp", 
  "status": "connected",
  "channel_data": {
    "phone_number": "+1234567890",
    "display_name": "My WhatsApp Business"
  }
}
```

**Response Schema**:
- `instance_name` (string): Instance name
- `channel_type` (string): Channel type
- `status` (string): Connection status (connected|disconnected|connecting|error)
- `channel_data` (object, optional): Channel-specific data

#### POST /api/v1/instances/{instance_name}/restart
Restart instance connection for any channel type.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "message": "Instance restarted successfully",
  "status": "restarting"
}
```

#### POST /api/v1/instances/{instance_name}/logout
Logout/disconnect instance for any channel type.

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "message": "Instance logged out successfully",
  "status": "disconnected"
}
```

#### DELETE /api/v1/instances/{instance_name}/channel
Delete instance from external channel service (keeps database record).

**Authentication**: Required

**Path Parameters**:
- `instance_name` (string): Name of the instance

**Response**:
```json
{
  "message": "Instance deleted from channel service",
  "status": "deleted"
}
```

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Validation error or invalid request"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing API key"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

---

## Integration Examples

### Creating a WhatsApp Instance

```bash
curl -X POST "http://localhost:8000/api/v1/instances" \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "business_whatsapp",
    "channel_type": "whatsapp",
    "evolution_url": "http://localhost:8080",
    "evolution_key": "your_evolution_key",
    "phone_number": "+1234567890",
    "agent_api_url": "http://localhost:3000",
    "agent_api_key": "your_agent_key",
    "default_agent": "support_agent"
  }'
```

### Getting QR Code

```bash
curl -X GET "http://localhost:8000/api/v1/instances/business_whatsapp/qr" \
  -H "Authorization: Bearer your_api_key"
```

### Webhook Integration

Your Evolution API should be configured to send webhooks to:
- Default instance: `http://your-domain.com/webhook/evolution`
- Specific instance: `http://your-domain.com/webhook/evolution/business_whatsapp`

---

## Channel-Specific Notes

### WhatsApp
- Requires Evolution API setup
- Supports QR code authentication
- Phone number validation during creation
- Session management with prefixes

### Slack (Future)
- Will use OAuth flow
- Returns `auth_url` for authorization
- Bot token management

### Discord (Future)
- Uses bot tokens
- Guild/server integration
- Invite link generation

---

## Development Notes

- API documentation available at `/api/v1/docs`
- Health check at `/health` (no auth required)
- All timestamps in UTC ISO format
- Multi-tenant architecture supports unlimited instances
- Backward compatibility maintained with default instance routing