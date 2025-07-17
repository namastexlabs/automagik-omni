# Automagik Omni API Documentation

*Generated automatically on Thu Jul 17 17:47:51 -03 2025 by the API documentation generator*

This document provides comprehensive examples for all Automagik Omni API endpoints with real curl commands, request/response examples, and usage patterns.

## Base URL


## Authentication
All protected endpoints require a Bearer token in the Authorization header:


## Content Type
All POST/PUT requests should use JSON content type:


## Table of Contents

1. [Health & System](#health--system)
2. [Instance Management](#instance-management)
3. [Instance Operations](#instance-operations)
4. [Message Sending](#message-sending)
5. [Trace & Analytics](#trace--analytics)
6. [Webhooks](#webhooks)
7. [Error Handling](#error-handling)
8. [Filtering & Pagination](#filtering--pagination)

---

## Health & System


### Health Check

**Endpoint:** `GET /health`

**cURL Example:**
```bash
curl -s -X GET -H 'Content-Type: application/json' http://localhost:18882/health
```

**Response (HTTP 200):**
```json
{
  "status": "healthy"
}
```

---


### Get Supported Channels

**Endpoint:** `GET /api/v1/instances/supported-channels`

**cURL Example:**
```bash
curl -s -X GET -H 'Authorization: Bearer namastex888' -H 'Content-Type: application/json' http://localhost:18882/api/v1/instances/supported-channels
```

**Response (HTTP 200):**
```json
{
  "supported_channels": [
    "whatsapp"
  ],
  "total_channels": 1
}
```

---


## Instance Management


### List All Instances

**Endpoint:** `GET /api/v1/instances`

**cURL Example:**
```bash
curl -s -X GET -H 'Authorization: Bearer namastex888' -H 'Content-Type: application/json' http://localhost:18882/api/v1/instances
```

**Response (HTTP 200):**
```json
[
  {
    "id": 1,
    "name": "aaaa",
    "channel_type": "whatsapp",
    "evolution_url": "http://172.19.209.168:18080",
    "evolution_key": "09A08CCA-C644-4555-83C2-D866348F5B68",
    "whatsapp_instance": "aaaa",
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
  },
  {
    "id": 2,
    "name": "afeafaefa",
    "channel_type": "whatsapp",
    "evolution_url": "http://172.19.209.168:18080",
    "evolution_key": "A12694AF-B4AA-41A6-AF02-ED9E85E9451E",
    "whatsapp_instance": "afeafaefa",
    "session_id_prefix": "automagik_",
    "webhook_base64": true,
    "agent_api_url": "http://172.19.209.168:18881",
    "agent_api_key": "namastex888",
    "default_agent": "discord",
    "agent_timeout": 60,
    "is_default": false,
    "is_active": false,
    "automagik_instance_id": "automagik-1752087186026-k28555wiq",
    "automagik_instance_name": "AutomagikAPI Local",
    "created_at": "2025-07-09T21:32:51.500255",
    "updated_at": "2025-07-09T21:32:56.880912",
    "evolution_status": {
      "state": "close",
      "owner_jid": null,
      "profile_name": null,
      "profile_picture_url": null,
      "last_updated": "2025-07-17T17:47:51.663644",
      "error": null
    }
  }
]
```

---

