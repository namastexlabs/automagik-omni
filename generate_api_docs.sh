#!/bin/bash

# Automagik Omni API Documentation Generator
# This script tests all API endpoints and generates comprehensive markdown documentation

set -e

# Configuration
API_BASE="http://localhost:18882"
API_KEY="namastex888"
OUTPUT_FILE="API_DOCUMENTATION.md"
TEMP_DIR="/tmp/automagik_api_test"
TEST_INSTANCE_NAME="test-doc-instance-$(date +%s)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create temp directory
mkdir -p "$TEMP_DIR"

# Function to make API calls and format output
api_call() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local description="$4"
    local auth_required="${5:-true}"
    
    log_info "Testing: $description"
    
    # Build curl command
    local curl_cmd="curl -s -X $method"
    
    if [ "$auth_required" = "true" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $API_KEY'"
    fi
    
    curl_cmd="$curl_cmd -H 'Content-Type: application/json'"
    
    if [ -n "$data" ]; then
        echo "$data" > "$TEMP_DIR/request.json"
        curl_cmd="$curl_cmd -d @$TEMP_DIR/request.json"
    fi
    
    curl_cmd="$curl_cmd $API_BASE$endpoint"
    
    # Execute and capture response
    local response
    local status_code
    
    if response=$(eval "$curl_cmd" 2>/dev/null); then
        status_code=$(eval "$curl_cmd -w '%{http_code}'" -o /dev/null 2>/dev/null)
        log_success "Response received (HTTP $status_code)"
    else
        log_error "Failed to call endpoint"
        response='{"error": "Failed to connect"}'
        status_code="000"
    fi
    
    # Format output for markdown
    cat >> "$OUTPUT_FILE" << EOF

### $description

**Endpoint:** \`$method $endpoint\`

**cURL Example:**
\`\`\`bash
$curl_cmd
\`\`\`

EOF

    if [ -n "$data" ]; then
        cat >> "$OUTPUT_FILE" << EOF
**Request Body:**
\`\`\`json
$(echo "$data" | jq . 2>/dev/null || echo "$data")
\`\`\`

EOF
    fi

    cat >> "$OUTPUT_FILE" << EOF
**Response (HTTP $status_code):**
\`\`\`json
$(echo "$response" | jq . 2>/dev/null || echo "$response")
\`\`\`

---

EOF
}

# Function to test message endpoints with specific instance
test_message_endpoints() {
    local instance_name="$1"
    
    log_info "Testing message endpoints for instance: $instance_name"
    
    # Test send text message
    api_call "POST" "/api/v1/instance/$instance_name/send-text" \
        '{"phone_number": "+5511999999999", "text": "Hello! This is a test message from the API documentation generator."}' \
        "Send Text Message"
    
    # Test send media message
    api_call "POST" "/api/v1/instance/$instance_name/send-media" \
        '{"phone_number": "+5511999999999", "media_url": "https://example.com/image.jpg", "caption": "Test image caption", "media_type": "image"}' \
        "Send Media Message"
    
    # Test send audio message
    api_call "POST" "/api/v1/instance/$instance_name/send-audio" \
        '{"phone_number": "+5511999999999", "audio_url": "https://example.com/audio.mp3", "caption": "Test audio"}' \
        "Send Audio Message"
    
    # Test send contact
    api_call "POST" "/api/v1/instance/$instance_name/send-contact" \
        '{"phone_number": "+5511999999999", "contact": {"name": "John Doe", "phone": "+5511888888888"}}' \
        "Send Contact"
    
    # Test send reaction
    api_call "POST" "/api/v1/instance/$instance_name/send-reaction" \
        '{"phone_number": "+5511999999999", "message_id": "test_message_id", "emoji": "👍"}' \
        "Send Reaction"
    
    # Test fetch profile
    api_call "POST" "/api/v1/instance/$instance_name/fetch-profile" \
        '{"phone_number": "+5511999999999"}' \
        "Fetch WhatsApp Profile"
}

# Start generating documentation
log_info "Starting API documentation generation..."

cat > "$OUTPUT_FILE" << EOF
# Automagik Omni API Documentation

*Generated automatically on $(date) by the API documentation generator*

This document provides comprehensive examples for all Automagik Omni API endpoints with real curl commands, request/response examples, and usage patterns.

## Base URL
```
http://localhost:18882
```

## Authentication
All protected endpoints require a Bearer token in the Authorization header:
```bash
-H "Authorization: Bearer your_api_key_here"
```

## Content Type
All POST/PUT requests should use JSON content type:
```bash
-H "Content-Type: application/json"
```

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

EOF

# Test health endpoint
api_call "GET" "/health" "" "Health Check" "false"

# Test supported channels
api_call "GET" "/api/v1/instances/supported-channels" "" "Get Supported Channels"

cat >> "$OUTPUT_FILE" << 'EOF'

## Instance Management

EOF

# Test instance management endpoints
api_call "GET" "/api/v1/instances" "" "List All Instances"

api_call "GET" "/api/v1/instances?skip=0&limit=5&include_status=true" "" "List Instances with Pagination and Status"

# Get first instance for testing (if any exist)
EXISTING_INSTANCE=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_BASE/api/v1/instances" | jq -r '.[0].name // empty' 2>/dev/null)

if [ -n "$EXISTING_INSTANCE" ]; then
    log_info "Using existing instance for testing: $EXISTING_INSTANCE"
    api_call "GET" "/api/v1/instances/$EXISTING_INSTANCE" "" "Get Specific Instance"
else
    log_warning "No existing instances found. Some tests will use placeholder responses."
fi

# Test instance creation (this will likely fail with auth error, but shows the format)
api_call "POST" "/api/v1/instances" \
    '{
        "name": "'$TEST_INSTANCE_NAME'",
        "channel_type": "whatsapp",
        "evolution_url": "http://172.19.209.168:18080",
        "evolution_key": "test-key-for-docs",
        "agent_api_url": "http://172.19.209.168:18881",
        "agent_api_key": "namastex888",
        "default_agent": "test-agent",
        "webhook_base64": false,
        "phone_number": "+5511999999999"
    }' \
    "Create New Instance"

# Test instance update
api_call "PUT" "/api/v1/instances/$TEST_INSTANCE_NAME" \
    '{
        "agent_api_url": "https://updated-agent.example.com",
        "webhook_base64": true,
        "default_agent": "updated-agent"
    }' \
    "Update Instance Configuration"

cat >> "$OUTPUT_FILE" << 'EOF'

## Instance Operations

EOF

# Use existing instance or test instance for operations
OPERATION_INSTANCE="${EXISTING_INSTANCE:-$TEST_INSTANCE_NAME}"

# Test instance operations
api_call "GET" "/api/v1/instances/$OPERATION_INSTANCE/qr" "" "Get QR Code for WhatsApp Connection"

api_call "GET" "/api/v1/instances/$OPERATION_INSTANCE/status" "" "Get Instance Connection Status"

api_call "POST" "/api/v1/instances/$OPERATION_INSTANCE/set-default" "" "Set Instance as Default"

api_call "POST" "/api/v1/instances/$OPERATION_INSTANCE/restart" "" "Restart Instance Connection"

api_call "POST" "/api/v1/instances/$OPERATION_INSTANCE/logout" "" "Logout Instance"

api_call "POST" "/api/v1/instances/discover" "" "Discover Evolution Instances"

cat >> "$OUTPUT_FILE" << 'EOF'

## Message Sending

EOF

# Test message endpoints
test_message_endpoints "$OPERATION_INSTANCE"

cat >> "$OUTPUT_FILE" << 'EOF'

## Trace & Analytics

EOF

# Test trace endpoints
api_call "GET" "/api/v1/traces" "" "List All Message Traces"

api_call "GET" "/api/v1/traces?limit=5&status=completed&instance_name=$OPERATION_INSTANCE" "" "List Traces with Filters"

api_call "GET" "/api/v1/traces?start_date=2025-01-01&end_date=2025-12-31&message_type=text" "" "List Traces by Date Range and Message Type"

# Get a trace ID if available
TRACE_ID=$(curl -s -H "Authorization: Bearer $API_KEY" "$API_BASE/api/v1/traces?limit=1" | jq -r '.[0].trace_id // empty' 2>/dev/null)

if [ -n "$TRACE_ID" ]; then
    api_call "GET" "/api/v1/traces/$TRACE_ID" "" "Get Specific Trace Details"
    api_call "GET" "/api/v1/traces/$TRACE_ID/payloads" "" "Get Trace Payloads"
fi

# Test analytics
api_call "GET" "/api/v1/analytics/summary" "" "Get Analytics Summary"

api_call "GET" "/api/v1/analytics/summary?start_date=2025-01-01&end_date=2025-12-31" "" "Get Analytics for Date Range"

cat >> "$OUTPUT_FILE" << 'EOF'

## Webhooks

EOF

# Test webhook simulation
api_call "POST" "/webhook/evolution/$OPERATION_INSTANCE" \
    '{
        "event": "messages.upsert",
        "data": {
            "messages": [{
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "id": "example_message_id_123"
                },
                "message": {
                    "conversation": "Hello! This is a test message from webhook."
                },
                "messageTimestamp": '$(date +%s)'
            }]
        },
        "instance": "'$OPERATION_INSTANCE'"
    }' \
    "Process Evolution API Webhook" "false"

# Test default webhook (backward compatibility)
api_call "POST" "/webhook/evolution" \
    '{
        "event": "messages.upsert",
        "data": {
            "messages": [{
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "id": "example_message_id_456"
                },
                "message": {
                    "conversation": "Hello! This is a test to default instance."
                },
                "messageTimestamp": '$(date +%s)'
            }]
        }
    }' \
    "Process Webhook to Default Instance" "false"

cat >> "$OUTPUT_FILE" << 'EOF'

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no response body
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid API key
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

### Error Response Format

All errors follow this format:

```json
{
    "detail": "Error description"
}
```

### Validation Error Format

For validation errors (422), you'll get detailed field information:

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "name"],
            "msg": "Field required",
            "input": {},
            "url": "https://errors.pydantic.dev/2.0/v/missing"
        }
    ]
}
```

### Common Error Examples

EOF

# Test some error scenarios
api_call "GET" "/api/v1/instances/nonexistent-instance" "" "Instance Not Found Error"

api_call "POST" "/api/v1/instances" \
    '{"name": ""}' \
    "Validation Error Example"

api_call "GET" "/api/v1/instances" "" "Unauthorized Error Example" "false"

cat >> "$OUTPUT_FILE" << 'EOF'

## Filtering & Pagination

### Instance Listing Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `skip` | integer | Number of records to skip | `skip=10` |
| `limit` | integer | Maximum records to return | `limit=5` |
| `include_status` | boolean | Include Evolution API status | `include_status=true` |

### Trace Filtering Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `skip` | integer | Number of records to skip | `skip=0` |
| `limit` | integer | Maximum records to return | `limit=20` |
| `status` | string | Filter by trace status | `status=completed` |
| `instance_name` | string | Filter by instance | `instance_name=my-instance` |
| `message_type` | string | Filter by message type | `message_type=text` |
| `start_date` | string | Start date (ISO format) | `start_date=2025-01-01` |
| `end_date` | string | End date (ISO format) | `end_date=2025-12-31` |
| `sender_phone` | string | Filter by sender phone | `sender_phone=5511999999999` |
| `has_media` | boolean | Filter by media presence | `has_media=true` |

### Example Filtered Requests

```bash
# Get recent completed text messages
curl -H "Authorization: Bearer your_key" \
  "http://localhost:18882/api/v1/traces?status=completed&message_type=text&limit=10"

# Get traces for specific instance in date range
curl -H "Authorization: Bearer your_key" \
  "http://localhost:18882/api/v1/traces?instance_name=my-instance&start_date=2025-07-01&end_date=2025-07-31"

# Get media messages only
curl -H "Authorization: Bearer your_key" \
  "http://localhost:18882/api/v1/traces?has_media=true&limit=5"
```

### Response Formats

All list endpoints return arrays of objects:

```json
[
    {
        "id": 1,
        "field1": "value1",
        "field2": "value2"
    },
    {
        "id": 2,
        "field1": "value3",
        "field2": "value4"
    }
]
```

Empty results return empty array:
```json
[]
```

## Development Notes

### Testing the API

1. **Start the development server:**
   ```bash
   make dev
   ```

2. **Use the interactive docs:**
   Visit `http://localhost:18882/api/v1/docs` for Swagger UI

3. **Health check:**
   ```bash
   curl http://localhost:18882/health
   ```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTOMAGIK_API_KEY` | API authentication key | `namastex888` |
| `AUTOMAGIK_API_HOST` | API server host | `0.0.0.0` |
| `AUTOMAGIK_API_PORT` | API server port | `18882` |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/automagik-omni.db` |

### Rate Limiting

Currently, there are no rate limits implemented, but consider implementing them for production use.

### Webhook Security

- Webhooks from Evolution API should be configured to use the correct instance-specific URLs
- Consider implementing webhook signature validation for production
- Monitor webhook processing through the traces API

---

*This documentation was generated automatically. For the latest API changes, regenerate using the `generate_api_docs.sh` script.*

EOF

# Clean up test instance if it was created (though it likely failed)
if [ "$TEST_INSTANCE_NAME" != "${EXISTING_INSTANCE:-}" ]; then
    log_info "Cleaning up test instance (if created): $TEST_INSTANCE_NAME"
    curl -s -X DELETE -H "Authorization: Bearer $API_KEY" "$API_BASE/api/v1/instances/$TEST_INSTANCE_NAME" >/dev/null 2>&1 || true
fi

# Clean up temp files
rm -rf "$TEMP_DIR"

log_success "API documentation generated: $OUTPUT_FILE"
log_info "Total size: $(wc -l < "$OUTPUT_FILE") lines"
log_info "Open the file to view comprehensive API documentation with real examples!"

# Optionally open the file (uncomment if you want)
# code "$OUTPUT_FILE" 2>/dev/null || open "$OUTPUT_FILE" 2>/dev/null || echo "Open $OUTPUT_FILE to view the documentation"