# Omni API - Complete Specification

**Version:** 0.2.0
**Base URL:** `http://192.168.112.138:8882`
**Authentication:** `x-api-key` header

---

## 📡 Endpoints Overview

### **Instances Management**
- `POST /api/v1/instances` - Create Instance
- `GET /api/v1/instances` - List Instances
- `GET /api/v1/instances/` - Get Omni Channels (all instances with health)
- `POST /api/v1/instances/discover` - Discover Instances
- `GET /api/v1/instances/supported-channels` - Get Supported Channels
- `GET /api/v1/instances/{instance_name}` - Get Instance
- `PUT /api/v1/instances/{instance_name}` - Update Instance
- `DELETE /api/v1/instances/{instance_name}` - Delete Instance

### **Instance Control**
- `POST /api/v1/instances/{instance_name}/connect` - Connect Instance
- `POST /api/v1/instances/{instance_name}/disconnect` - Disconnect Instance
- `POST /api/v1/instances/{instance_name}/restart` - Restart Instance
- `POST /api/v1/instances/{instance_name}/logout` - Logout Instance
- `GET /api/v1/instances/{instance_name}/status` - Get Connection Status
- `GET /api/v1/instances/{instance_name}/qr` - Get QR Code

### **Messaging (Send)**
- `POST /api/v1/instance/{instance_name}/send-text` - Send Text Message
- `POST /api/v1/instance/{instance_name}/send-media` - Send Media Message
- `POST /api/v1/instance/{instance_name}/send-audio` - Send Audio Message
- `POST /api/v1/instance/{instance_name}/send-sticker` - Send Sticker Message
- `POST /api/v1/instance/{instance_name}/send-contact` - Send Contact Message
- `POST /api/v1/instance/{instance_name}/send-reaction` - Send Reaction Message

### **Omni Channel Abstraction (Read)**
- `GET /api/v1/instances/{instance_name}/chats` - Get Omni Chats (paginated, filtered)
- `GET /api/v1/instances/{instance_name}/chats/{chat_id}` - Get Omni Chat By Id
- `GET /api/v1/instances/{instance_name}/contacts` - Get Omni Contacts (paginated, searchable)
- `GET /api/v1/instances/{instance_name}/contacts/{contact_id}` - Get Omni Contact By Id

### **Traces & Analytics**
- `GET /api/v1/traces` - List Traces (with filters)
- `GET /api/v1/traces/{trace_id}` - Get Trace
- `GET /api/v1/traces/{trace_id}/payloads` - **Get Trace Payloads** ⭐ (includes message content & media)
- `GET /api/v1/traces/phone/{phone_number}` - Get Traces By Phone
- `GET /api/v1/traces/analytics/summary` - Get Trace Analytics
- `DELETE /api/v1/traces/cleanup` - Cleanup Old Traces

### **Profile Management**
- `POST /api/v1/instance/{instance_name}/fetch-profile` - Fetch User Profile
- `POST /api/v1/instance/{instance_name}/update-profile-picture` - Update Profile Picture

### **Access Control**
- `GET /api/v1/access/rules` - List Access Rules
- `POST /api/v1/access/rules` - Create Access Rule
- `DELETE /api/v1/access/rules/{rule_id}` - Delete Access Rule

### **System**
- `GET /health` - Health Check
- `POST /webhook/evolution/{instance_name}` - Evolution Webhook Tenant

---

## 🔑 Key Schemas

### TracePayloadResponse
Contains the **FULL message content** including media URLs:

```json
{
  "id": 123,
  "trace_id": "uuid",
  "stage": "incoming|agent_request|agent_response|outgoing",
  "payload_type": "whatsapp_webhook|agent_api_call|etc",
  "timestamp": "2025-11-18T...",
  "contains_media": true,
  "contains_base64": false,
  "payload": {
    // Full WhatsApp message structure here
    "data": {
      "message": {
        "imageMessage": {
          "url": "https://...",
          "caption": "...",
          "mimetype": "image/jpeg"
        },
        "audioMessage": {
          "url": "https://...",
          "mimetype": "audio/ogg; codecs=opus",
          "ptt": true
        },
        "videoMessage": { ... },
        "documentMessage": { ... },
        "stickerMessage": { ... }
      }
    }
  }
}
```

### TraceResponse
Metadata about a message (no content):

```json
{
  "trace_id": "uuid",
  "instance_name": "genie",
  "sender_phone": "+5511999999999",
  "sender_name": "John Doe",
  "message_type": "text|image|audio|video|document|sticker",
  "status": "received|processing|completed|failed",
  "has_media": true,
  "received_at": "2025-11-18T...",
  "completed_at": "2025-11-18T..."
}
```

---

## 🎯 Multimodal Strategy

To read messages with **full content including media**:

1. **Get trace metadata**: `GET /api/v1/traces` (filter by instance/phone/time)
2. **Get trace payloads**: `GET /api/v1/traces/{trace_id}/payloads?include_payload=true`
3. **Extract media URLs** from payload:
   - `payload.data.message.imageMessage.url`
   - `payload.data.message.audioMessage.url`
   - `payload.data.message.videoMessage.url`
   - `payload.data.message.documentMessage.url`
   - etc.
4. **Download media** from URL
5. **Process media**:
   - Images: Claude can view directly
   - Audio: Transcribe with Whisper
   - Documents: Extract text (pypdf, python-docx, etc.)
   - Video: Extract frames/transcribe audio

---

## 📦 Already Implemented in Client

✅ All send operations (text, media, audio, sticker, contact, reaction)
✅ Instance management (list, get, create, update, delete, status, qr)
✅ Trace operations (list, get, get_payloads, analytics, by_phone, cleanup)
✅ Profile operations (fetch, update_picture)
✅ Chat operations (list, get)
✅ Contact operations (list, get)
✅ Channel operations (list_channels)

## 🚧 TODO for Full Multimodal

- [ ] Download media from URLs in payloads
- [ ] Store media locally (`.genie/whatsapp-media/`)
- [ ] Process audio with Whisper (transcription)
- [ ] Extract text from PDFs/documents
- [ ] Enhanced reading tools that show actual content
- [ ] Tool to read messages with content: `read_messages_with_content()`

---

## 💡 Implementation Notes

**Current genie-omni client already has:**
- `get_trace_payloads(trace_id, include_payload=True)` ✅

**Need to add:**
- Media downloader helper
- Whisper integration for audio
- Document text extraction
- Enhanced MCP tools that fetch payloads + process media
