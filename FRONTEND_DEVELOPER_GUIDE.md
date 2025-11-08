# Automagik Omni - Frontend Developer Guide

**Version:** 1.0
**Last Updated:** 2025-11-04
**API Version:** v1

---

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Quick Start](#quick-start)
3. [Architecture Overview](#architecture-overview)
4. [Authentication & Security](#authentication--security)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Data Models & TypeScript Types](#data-models--typescript-types)
7. [Real-World Examples](#real-world-examples)
8. [Best Practices](#best-practices)
9. [Error Handling](#error-handling)
10. [Testing Strategies](#testing-strategies)

---

## Introduction

### What is Automagik Omni?

Automagik Omni is a **multi-tenant messaging orchestration platform** that provides a unified API for managing communications across multiple channels:

- **WhatsApp** (via Evolution API with Baileys)
- **Discord** (native bot integration)
- Future channels (Telegram, Slack, etc.)

### Why Use Omni for Your Frontend?

✅ **Channel Abstraction** - Write once, support multiple platforms
✅ **Unified Data Models** - Consistent contacts, chats, messages across channels
✅ **Type Safety** - Pydantic schemas translate to TypeScript types
✅ **Multi-Tenant** - Manage multiple instances/bots from one API
✅ **Built-in Analytics** - Message tracing and performance monitoring
✅ **Access Control** - Phone number allow/block rules

### Prerequisites

- Node.js 18+ or modern browser
- Basic understanding of REST APIs
- TypeScript knowledge (recommended)
- API key from your Omni installation

---

## Quick Start

### 1. Installation

```bash
npm install axios zod  # Or your preferred HTTP client
```

### 2. Basic Configuration

```typescript
// omni-config.ts
export const OMNI_CONFIG = {
  apiUrl: process.env.NEXT_PUBLIC_OMNI_API_URL || 'http://localhost:8882',
  apiKey: process.env.NEXT_PUBLIC_OMNI_API_KEY || '',
  defaultTimeout: 30000,
};
```

### 3. Create API Client

```typescript
// omni-client.ts
import axios, { AxiosInstance, AxiosError } from 'axios';
import { OMNI_CONFIG } from './omni-config';

export class OmniApiClient {
  private client: AxiosInstance;

  constructor(apiKey?: string, baseURL?: string) {
    this.client = axios.create({
      baseURL: baseURL || OMNI_CONFIG.apiUrl,
      timeout: OMNI_CONFIG.defaultTimeout,
      headers: {
        'x-api-key': apiKey || OMNI_CONFIG.apiKey,
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          console.error('Authentication failed - check API key');
        }
        throw error;
      }
    );
  }

  // Instance Management
  async listInstances(includeStatus = true) {
    const { data } = await this.client.get('/api/v1/instances', {
      params: { include_status: includeStatus },
    });
    return data;
  }

  async createInstance(config: InstanceCreate) {
    const { data } = await this.client.post('/api/v1/instances', config);
    return data;
  }

  async deleteInstance(name: string) {
    const { data } = await this.client.delete(`/api/v1/instances/${name}`);
    return data;
  }

  // Omni Contacts
  async getContacts(instanceName: string, params?: ContactsParams) {
    const { data } = await this.client.get(
      `/api/v1/instances/${instanceName}/contacts`,
      { params }
    );
    return data;
  }

  // Omni Chats
  async getChats(instanceName: string, params?: ChatsParams) {
    const { data } = await this.client.get(
      `/api/v1/instances/${instanceName}/chats`,
      { params }
    );
    return data;
  }

  // Omni Messages
  async getChatMessages(instanceName: string, chatId: string, params?: MessagesParams) {
    const { data } = await this.client.get(
      `/api/v1/instances/${instanceName}/chats/${chatId}/messages`,
      { params }
    );
    return data;
  }

  // Message Sending
  async sendText(instanceName: string, message: SendTextRequest) {
    const { data } = await this.client.post(
      `/api/v1/instance/${instanceName}/send-text`,
      message
    );
    return data;
  }

  async sendMedia(instanceName: string, message: SendMediaRequest) {
    const { data } = await this.client.post(
      `/api/v1/instance/${instanceName}/send-media`,
      message
    );
    return data;
  }

  // Access Control
  async listAccessRules(filters?: AccessRuleFilters) {
    const { data } = await this.client.get('/api/v1/access/rules', {
      params: filters,
    });
    return data;
  }

  async createAccessRule(rule: AccessRuleCreate) {
    const { data } = await this.client.post('/api/v1/access/rules', rule);
    return data;
  }

  // Traces & Analytics
  async listTraces(filters?: TraceFilters) {
    const { data } = await this.client.get('/api/v1/traces', {
      params: filters,
    });
    return data;
  }

  async getAnalytics(filters?: AnalyticsFilters) {
    const { data } = await this.client.get('/api/v1/traces/analytics/summary', {
      params: filters,
    });
    return data;
  }
}

// Singleton instance
export const omniClient = new OmniApiClient();
```

### 4. Use in React Component

```typescript
// App.tsx
import { useEffect, useState } from 'react';
import { omniClient } from './omni-client';

function InstancesList() {
  const [instances, setInstances] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchInstances() {
      try {
        const data = await omniClient.listInstances();
        setInstances(data);
      } catch (error) {
        console.error('Failed to fetch instances:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchInstances();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {instances.map((instance) => (
        <div key={instance.id}>
          <h3>{instance.name}</h3>
          <p>Channel: {instance.channel_type}</p>
          <p>Status: {instance.evolution_status?.state || 'N/A'}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## Architecture Overview

### System Layers

```
┌─────────────────────────────────────────┐
│         Your Frontend Application       │
│   (React, Vue, Angular, Mobile, etc.)   │
└───────────────┬─────────────────────────┘
                │ HTTPS / REST
                │ x-api-key header
                ↓
┌─────────────────────────────────────────┐
│       Automagik Omni API (FastAPI)      │
│                                         │
│  • Instance Management                  │
│  • Omni Channel Abstraction             │
│  • Message Routing                      │
│  • Access Control                       │
│  • Tracing & Analytics                  │
└───────────┬──────────────┬──────────────┘
            │              │
            ↓              ↓
  ┌─────────────────┐  ┌──────────────┐
  │ Evolution API   │  │ Discord API  │
  │  (WhatsApp)     │  │              │
  └─────────────────┘  └──────────────┘
```

### Key Concepts

**1. Instances**
An instance represents a configured channel connection (one WhatsApp account, one Discord bot, etc.).

**2. Omni Abstraction**
Unified data models for contacts, chats, and messages across all channels.

**3. Multi-Tenancy**
Multiple instances can coexist, each with independent configuration and access control.

**4. Message Tracing**
Every message is traced from webhook → agent processing → response, with full payload logging.

---

## Authentication & Security

### API Key Authentication

**All endpoints require `x-api-key` header:**

```typescript
headers: {
  'x-api-key': 'your-api-key-here',
  'Content-Type': 'application/json'
}
```

### Configuration

Set via environment variable on the API server:

```bash
AUTOMAGIK_OMNI_API_KEY=your-secret-key-here
```

### Security Best Practices

```typescript
// ❌ NEVER hardcode API keys
const client = new OmniApiClient('hardcoded-key-bad');

// ✅ Use environment variables
const client = new OmniApiClient(process.env.NEXT_PUBLIC_OMNI_API_KEY);

// ✅ Store in secure backend proxy
// Frontend → Your backend → Omni API
```

### Error Responses

**401 Unauthorized**
```json
{
  "detail": "Missing API key"
}
```

**403 Forbidden** (Access Control)
```json
{
  "status": "blocked",
  "reason": "access_denied",
  "phone": "+5511999999999"
}
```

**404 Not Found**
```json
{
  "detail": "Instance 'my-bot' not found"
}
```

---

## API Endpoints Reference

### Base URL

```
http://localhost:8882/api/v1
```

### Instance Management

#### List Instances
```http
GET /instances?skip=0&limit=100&include_status=true
```

**Response:**
```typescript
Instance[] // Array of InstanceConfigResponse objects
```

#### Get Instance
```http
GET /instances/{instance_name}?include_status=true
```

#### Create Instance
```http
POST /instances
Content-Type: application/json

{
  "name": "my-whatsapp-bot",
  "channel_type": "whatsapp",
  "evolution_url": "http://192.168.1.100:8080",
  "evolution_key": "your-evolution-key",
  "phone_number": "+5511999999999",
  "agent_api_url": "https://api.automagik.com/v1",
  "agent_api_key": "your-agent-key",
  "agent_id": "your-agent-id",
  "agent_timeout": 60,
  "enable_auto_split": true
}
```

**Response:** `201 Created` with created instance

#### Update Instance
```http
PUT /instances/{instance_name}

{
  "agent_timeout": 120,
  "enable_auto_split": false
}
```

#### Delete Instance
```http
DELETE /instances/{instance_name}
```

**Response:**
```json
{
  "message": "Instance 'my-bot' deleted successfully"
}
```

### Connection Management

#### Get QR Code (WhatsApp)
```http
GET /instances/{instance_name}/qr
```

**Response:**
```json
{
  "instance_name": "my-bot",
  "channel_type": "whatsapp",
  "qr_code": "data:image/png;base64,iVBORw0KGgo...",
  "status": "pending",
  "message": "Scan QR code with WhatsApp"
}
```

#### Get Connection Status
```http
GET /instances/{instance_name}/status
```

**Response:**
```json
{
  "instance_name": "my-bot",
  "channel_type": "whatsapp",
  "status": "connected",
  "connected": true,
  "channel_data": {
    "profile_name": "My Business",
    "phone_number": "+5511999999999"
  }
}
```

#### Connect/Disconnect/Restart
```http
POST /instances/{instance_name}/connect
POST /instances/{instance_name}/disconnect
POST /instances/{instance_name}/restart
```

### Omni API - Unified Channel Access

#### Get Contacts
```http
GET /instances/{instance_name}/contacts?page=1&page_size=50&search_query=John
```

**Response:**
```json
{
  "contacts": [
    {
      "id": "5511999999999@s.whatsapp.net",
      "name": "John Doe",
      "channel_type": "whatsapp",
      "instance_name": "my-bot",
      "avatar_url": "https://example.com/avatar.jpg",
      "status": "online",
      "is_verified": true,
      "is_business": false,
      "channel_data": {},
      "last_seen": "2025-11-04T12:00:00Z"
    }
  ],
  "total_count": 150,
  "page": 1,
  "page_size": 50,
  "has_more": true
}
```

#### Get Chats
```http
GET /instances/{instance_name}/chats?page=1&chat_type_filter=direct
```

**Response:**
```json
{
  "chats": [
    {
      "id": "5511999999999@s.whatsapp.net",
      "name": "John Doe",
      "chat_type": "direct",
      "channel_type": "whatsapp",
      "participant_count": 2,
      "is_muted": false,
      "is_archived": false,
      "unread_count": 3,
      "last_message_at": "2025-11-04T12:30:00Z"
    }
  ],
  "total_count": 45,
  "page": 1,
  "has_more": false
}
```

#### Get Chat Messages
```http
GET /instances/{instance_name}/chats/{chat_id}/messages?page=1&page_size=50
```

**Response:**
```json
{
  "messages": [
    {
      "id": "3EB0XXXXXXXXXXXX",
      "chat_id": "5511999999999@s.whatsapp.net",
      "sender_id": "5511999999999@s.whatsapp.net",
      "sender_name": "John Doe",
      "message_type": "text",
      "text": "Hello, how are you?",
      "is_from_me": false,
      "timestamp": "2025-11-04T12:30:00Z"
    }
  ],
  "total_count": 125,
  "page": 1,
  "has_more": true
}
```

### Message Sending

#### Send Text Message
```http
POST /instance/{instance_name}/send-text

{
  "phone_number": "+5511999999999",
  "text": "Hello! How can I help you?",
  "quoted_message_id": null
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "3EB0YYYYYYYYYYYY",
  "status": "sent"
}
```

#### Send Media (Image/Video/Document)
```http
POST /instance/{instance_name}/send-media

{
  "phone_number": "+5511999999999",
  "media_type": "image",
  "media_url": "https://example.com/image.jpg",
  "caption": "Check this out!"
}
```

#### Send Audio
```http
POST /instance/{instance_name}/send-audio

{
  "phone_number": "+5511999999999",
  "audio_url": "https://example.com/voice.ogg"
}
```

#### Send Reaction
```http
POST /instance/{instance_name}/send-reaction

{
  "phone_number": "+5511999999999",
  "message_id": "3EB0XXXXXXXXXXXX",
  "reaction": "👍"
}
```

### Access Control

#### List Access Rules
```http
GET /access/rules?instance_name=my-bot&rule_type=block
```

**Response:**
```json
[
  {
    "id": 1,
    "instance_name": "my-bot",
    "phone_number": "+5511888888888",
    "rule_type": "block",
    "created_at": "2025-11-04T10:00:00Z"
  }
]
```

#### Create Access Rule
```http
POST /access/rules

{
  "phone_number": "+5511999999999",
  "rule_type": "allow",
  "instance_name": "my-bot"  // or null for global
}
```

#### Delete Access Rule
```http
DELETE /access/rules/{rule_id}
```

### Traces & Analytics

#### List Traces
```http
GET /traces?instance_name=my-bot&trace_status=failed&limit=50
```

**Response:**
```json
[
  {
    "trace_id": "abc-123-def",
    "instance_name": "my-bot",
    "sender_phone": "+5511999999999",
    "message_type": "conversation",
    "status": "completed",
    "received_at": "2025-11-04T12:30:00Z",
    "agent_processing_time_ms": 1500,
    "agent_response_success": true
  }
]
```

#### Get Analytics Summary
```http
GET /traces/analytics/summary?start_date=2025-11-01T00:00:00Z&instance_name=my-bot
```

**Response:**
```json
{
  "total_messages": 1250,
  "successful_messages": 1200,
  "failed_messages": 50,
  "success_rate": 96.0,
  "avg_processing_time_ms": 1800.5,
  "message_types": {
    "conversation": 1000,
    "imageMessage": 150,
    "audioMessage": 50
  }
}
```

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T12:30:00Z",
  "services": {
    "api": {
      "status": "up",
      "checks": {
        "database": "connected",
        "runtime": "operational"
      }
    }
  }
}
```

---

## Data Models & TypeScript Types

### Core Types

```typescript
// enums.ts
export type ChannelType = 'whatsapp' | 'discord';

export type OmniContactStatus = 'online' | 'offline' | 'away' | 'dnd' | 'unknown';

export type OmniChatType = 'direct' | 'group' | 'channel' | 'thread';

export type OmniMessageType =
  | 'text'
  | 'image'
  | 'video'
  | 'audio'
  | 'document'
  | 'sticker'
  | 'contact'
  | 'location'
  | 'reaction'
  | 'system'
  | 'unknown';

export type AccessRuleType = 'allow' | 'block';

export type TraceStatus =
  | 'received'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'access_denied';
```

### Instance Models

```typescript
// instance.types.ts
export interface InstanceCreate {
  name: string;
  channel_type: ChannelType;

  // WhatsApp specific
  evolution_url?: string;
  evolution_key?: string;
  whatsapp_instance?: string;
  phone_number?: string;
  auto_qr?: boolean;

  // Discord specific
  discord_bot_token?: string;
  discord_client_id?: string;
  discord_guild_id?: string;

  // Agent configuration
  agent_api_url: string;
  agent_api_key: string;
  agent_id?: string;
  agent_timeout?: number;
  enable_auto_split?: boolean;
}

export interface InstanceConfigResponse {
  id: number;
  name: string;
  channel_type: ChannelType;

  evolution_url?: string;
  evolution_key?: string;
  whatsapp_instance?: string;

  discord_client_id?: string;
  discord_guild_id?: string;
  has_discord_bot_token?: boolean;  // Token never exposed

  agent_api_url: string;
  agent_id?: string;
  agent_timeout: number;

  profile_name?: string;
  profile_pic_url?: string;
  owner_jid?: string;

  is_active: boolean;
  is_default: boolean;
  enable_auto_split: boolean;

  created_at: string;
  updated_at: string;

  evolution_status?: EvolutionStatus;
}

export interface EvolutionStatus {
  state: 'open' | 'connecting' | 'close';
  owner_jid?: string;
  profile_name?: string;
  profile_picture_url?: string;
  last_updated: string;
  error?: string;
}

export interface ConnectionStatus {
  instance_name: string;
  channel_type: ChannelType;
  status: string;
  connected: boolean;
  channel_data: Record<string, any>;
}

export interface QRCodeResponse {
  instance_name: string;
  channel_type: ChannelType;
  qr_code: string | null;
  base64?: string | null;
  message?: string;
  status?: string;
}
```

### Omni Models

```typescript
// omni.types.ts
export interface OmniContact {
  id: string;
  name: string;
  channel_type: ChannelType;
  instance_name: string;
  avatar_url?: string;
  status: OmniContactStatus;
  is_verified?: boolean;
  is_business?: boolean;
  channel_data: Record<string, any>;
  created_at?: string;
  last_seen?: string;
}

export interface OmniContactsResponse {
  contacts: OmniContact[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
  instance_name: string;
  channel_type: ChannelType;
  partial_errors: any[];
}

export interface OmniChat {
  id: string;
  name: string;
  chat_type: OmniChatType;
  channel_type: ChannelType;
  instance_name: string;
  participant_count?: number;
  is_muted: boolean;
  is_archived: boolean;
  is_pinned: boolean;
  description?: string;
  avatar_url?: string;
  unread_count?: number;
  channel_data: Record<string, any>;
  created_at?: string;
  last_message_at?: string;
}

export interface OmniChatsResponse {
  chats: OmniChat[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
  instance_name: string;
  channel_type: ChannelType;
  partial_errors: any[];
}

export interface OmniMessage {
  id: string;
  chat_id: string;
  sender_id: string;
  sender_name?: string;
  message_type: OmniMessageType;
  text?: string;
  media_url?: string;
  media_mime_type?: string;
  media_size?: number;
  caption?: string;
  thumbnail_url?: string;
  is_from_me: boolean;
  is_forwarded: boolean;
  is_reply: boolean;
  reply_to_message_id?: string;
  timestamp: string;
  edited_at?: string;
  channel_type: ChannelType;
  instance_name: string;
  channel_data: Record<string, any>;
}

export interface OmniMessagesResponse {
  messages: OmniMessage[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
  instance_name: string;
  chat_id: string;
  channel_type: ChannelType;
  partial_errors: any[];
}
```

### Message Sending Models

```typescript
// messages.types.ts
export interface SendTextRequest {
  user_id?: string;
  phone_number?: string;
  text: string;
  quoted_message_id?: string;
  auto_parse_mentions?: boolean;
  mentioned?: string[];
  mentions_everyone?: boolean;
  split_message?: boolean | null;
}

export interface SendMediaRequest {
  user_id?: string;
  phone_number?: string;
  media_type: 'image' | 'video' | 'document';
  media_url?: string;
  media_base64?: string;
  mime_type?: string;
  caption?: string;
  filename?: string;
}

export interface SendAudioRequest {
  user_id?: string;
  phone_number?: string;
  audio_url?: string;
  audio_base64?: string;
}

export interface SendReactionRequest {
  user_id?: string;
  phone_number?: string;
  message_id: string;
  reaction: string;
}

export interface MessageResponse {
  success: boolean;
  message_id?: string | null;
  status: string;
  evolution_response?: any;
  error?: string | null;
}
```

### Access Control Models

```typescript
// access.types.ts
export interface AccessRuleCreate {
  phone_number: string;  // E.164 format, supports trailing * wildcard
  rule_type: AccessRuleType;
  instance_name?: string | null;  // null = global rule
}

export interface AccessRule {
  id: number;
  instance_name?: string | null;
  phone_number: string;
  rule_type: AccessRuleType;
  created_at: string;
  updated_at: string;
}
```

### Trace Models

```typescript
// traces.types.ts
export interface MessageTrace {
  trace_id: string;
  instance_name: string;
  whatsapp_message_id?: string;
  sender_phone?: string;
  sender_name?: string;
  message_type?: string;
  message_type_display?: string;
  has_media: boolean;
  has_quoted_message: boolean;
  session_name?: string;
  agent_session_id?: string;
  status: TraceStatus;
  error_message?: string;
  error_stage?: string;
  received_at?: string;
  completed_at?: string;
  agent_processing_time_ms?: number;
  total_processing_time_ms?: number;
  agent_response_success?: boolean;
  evolution_success?: boolean;
}

export interface TraceAnalytics {
  total_messages: number;
  successful_messages: number;
  failed_messages: number;
  success_rate: number;
  avg_processing_time_ms: number;
  avg_agent_time_ms: number;
  message_types: Record<string, number>;
  error_stages?: Record<string, number>;
  instances?: Record<string, number>;
}
```

---

## Real-World Examples

### Example 1: Multi-Instance Chat Dashboard

```typescript
import { useState, useEffect } from 'react';
import { omniClient } from './omni-client';

interface ChatDashboardProps {
  instanceNames: string[];
}

export function ChatDashboard({ instanceNames }: ChatDashboardProps) {
  const [chats, setChats] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAllChats() {
      try {
        setLoading(true);
        const chatData: Record<string, any[]> = {};

        // Fetch chats from all instances in parallel
        await Promise.all(
          instanceNames.map(async (instance) => {
            try {
              const response = await omniClient.getChats(instance, {
                page: 1,
                page_size: 20,
                chat_type_filter: 'direct',
              });
              chatData[instance] = response.chats;
            } catch (err) {
              console.error(`Failed to load chats for ${instance}:`, err);
              chatData[instance] = [];
            }
          })
        );

        setChats(chatData);
      } catch (err) {
        setError('Failed to load chats');
      } finally {
        setLoading(false);
      }
    }

    loadAllChats();
  }, [instanceNames]);

  if (loading) return <div>Loading chats...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {instanceNames.map((instance) => (
        <div key={instance}>
          <h2>{instance}</h2>
          <div className="chats-grid">
            {chats[instance]?.map((chat) => (
              <ChatCard key={chat.id} chat={chat} instanceName={instance} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ChatCard({ chat, instanceName }: { chat: any; instanceName: string }) {
  return (
    <div className="chat-card">
      <img src={chat.avatar_url || '/default-avatar.png'} alt={chat.name} />
      <div>
        <h3>{chat.name}</h3>
        <p>{chat.chat_type} • {chat.unread_count} unread</p>
        <span>{new Date(chat.last_message_at).toLocaleString()}</span>
      </div>
    </div>
  );
}
```

### Example 2: Message Composer with Validation

```typescript
import { useState } from 'react';
import { omniClient } from './omni-client';
import { SendTextRequest, SendMediaRequest } from './types';

interface MessageComposerProps {
  instanceName: string;
  onSuccess?: () => void;
}

export function MessageComposer({ instanceName, onSuccess }: MessageComposerProps) {
  const [messageType, setMessageType] = useState<'text' | 'media'>('text');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [textMessage, setTextMessage] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');
  const [caption, setCaption] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Validate E.164 phone format
  const validatePhone = (phone: string): boolean => {
    return /^\+[1-9]\d{1,14}$/.test(phone);
  };

  const handleSendText = async () => {
    if (!validatePhone(phoneNumber)) {
      setError('Invalid phone number. Use E.164 format: +5511999999999');
      return;
    }

    if (!textMessage.trim()) {
      setError('Message cannot be empty');
      return;
    }

    setSending(true);
    setError(null);

    try {
      const request: SendTextRequest = {
        phone_number: phoneNumber,
        text: textMessage,
      };

      const response = await omniClient.sendText(instanceName, request);

      if (response.success) {
        setTextMessage('');
        onSuccess?.();
      } else {
        setError(response.error || 'Failed to send message');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Network error');
    } finally {
      setSending(false);
    }
  };

  const handleSendMedia = async () {
    if (!validatePhone(phoneNumber)) {
      setError('Invalid phone number. Use E.164 format: +5511999999999');
      return;
    }

    if (!mediaUrl.trim()) {
      setError('Media URL cannot be empty');
      return;
    }

    setSending(true);
    setError(null);

    try {
      const request: SendMediaRequest = {
        phone_number: phoneNumber,
        media_type: 'image',
        media_url: mediaUrl,
        caption: caption || undefined,
      };

      const response = await omniClient.sendMedia(instanceName, request);

      if (response.success) {
        setMediaUrl('');
        setCaption('');
        onSuccess?.();
      } else {
        setError(response.error || 'Failed to send media');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Network error');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="message-composer">
      <h3>Send Message via {instanceName}</h3>

      <div>
        <label>Phone Number (E.164 format)</label>
        <input
          type="tel"
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(e.target.value)}
          placeholder="+5511999999999"
        />
      </div>

      <div>
        <label>Message Type</label>
        <select value={messageType} onChange={(e) => setMessageType(e.target.value as any)}>
          <option value="text">Text</option>
          <option value="media">Media (Image)</option>
        </select>
      </div>

      {messageType === 'text' ? (
        <div>
          <label>Message</label>
          <textarea
            value={textMessage}
            onChange={(e) => setTextMessage(e.target.value)}
            rows={4}
            placeholder="Type your message..."
          />
          <button onClick={handleSendText} disabled={sending}>
            {sending ? 'Sending...' : 'Send Text'}
          </button>
        </div>
      ) : (
        <div>
          <label>Media URL</label>
          <input
            type="url"
            value={mediaUrl}
            onChange={(e) => setMediaUrl(e.target.value)}
            placeholder="https://example.com/image.jpg"
          />
          <label>Caption (optional)</label>
          <input
            type="text"
            value={caption}
            onChange={(e) => setCaption(e.target.value)}
            placeholder="Image caption"
          />
          <button onClick={handleSendMedia} disabled={sending}>
            {sending ? 'Sending...' : 'Send Media'}
          </button>
        </div>
      )}

      {error && <div className="error">{error}</div>}
    </div>
  );
}
```

### Example 3: Real-Time Analytics Dashboard

```typescript
import { useState, useEffect } from 'react';
import { omniClient } from './omni-client';
import { TraceAnalytics } from './types';

export function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState<TraceAnalytics | null>(null);
  const [timeRange, setTimeRange] = useState<'day' | 'week' | 'month'>('day');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAnalytics() {
      setLoading(true);
      try {
        const now = new Date();
        let startDate: Date;

        switch (timeRange) {
          case 'day':
            startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            break;
          case 'week':
            startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            break;
          case 'month':
            startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
            break;
        }

        const data = await omniClient.getAnalytics({
          start_date: startDate.toISOString(),
          end_date: now.toISOString(),
        });

        setAnalytics(data);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
      } finally {
        setLoading(false);
      }
    }

    fetchAnalytics();

    // Refresh every 30 seconds
    const interval = setInterval(fetchAnalytics, 30000);
    return () => clearInterval(interval);
  }, [timeRange]);

  if (loading) return <div>Loading analytics...</div>;
  if (!analytics) return <div>No data available</div>;

  return (
    <div className="analytics-dashboard">
      <h2>Message Analytics</h2>

      <div>
        <button onClick={() => setTimeRange('day')}>Last 24h</button>
        <button onClick={() => setTimeRange('week')}>Last 7d</button>
        <button onClick={() => setTimeRange('month')}>Last 30d</button>
      </div>

      <div className="metrics-grid">
        <MetricCard
          title="Total Messages"
          value={analytics.total_messages}
          color="blue"
        />
        <MetricCard
          title="Success Rate"
          value={`${analytics.success_rate.toFixed(1)}%`}
          color="green"
        />
        <MetricCard
          title="Failed Messages"
          value={analytics.failed_messages}
          color="red"
        />
        <MetricCard
          title="Avg Processing Time"
          value={`${analytics.avg_processing_time_ms.toFixed(0)}ms`}
          color="purple"
        />
      </div>

      <div className="message-types">
        <h3>Message Types</h3>
        <ul>
          {Object.entries(analytics.message_types).map(([type, count]) => (
            <li key={type}>
              {type}: {count}
            </li>
          ))}
        </ul>
      </div>

      {analytics.instances && (
        <div className="instances">
          <h3>Messages by Instance</h3>
          <ul>
            {Object.entries(analytics.instances).map(([instance, count]) => (
              <li key={instance}>
                {instance}: {count}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function MetricCard({ title, value, color }: any) {
  return (
    <div className={`metric-card metric-${color}`}>
      <h4>{title}</h4>
      <div className="value">{value}</div>
    </div>
  );
}
```

### Example 4: Access Control Manager

```typescript
import { useState, useEffect } from 'react';
import { omniClient } from './omni-client';
import { AccessRule, AccessRuleCreate } from './types';

export function AccessControlManager({ instanceName }: { instanceName?: string }) {
  const [rules, setRules] = useState<AccessRule[]>([]);
  const [newPhone, setNewPhone] = useState('');
  const [newRuleType, setNewRuleType] = useState<'allow' | 'block'>('allow');
  const [isGlobal, setIsGlobal] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadRules = async () => {
    setLoading(true);
    try {
      const data = await omniClient.listAccessRules({
        instance_name: instanceName,
      });
      setRules(data);
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, [instanceName]);

  const handleCreateRule = async () => {
    if (!/^\+[1-9]\d{1,14}\*?$/.test(newPhone)) {
      alert('Invalid phone number. Use E.164 format (+5511999999999) or wildcard (+5511*)');
      return;
    }

    try {
      const request: AccessRuleCreate = {
        phone_number: newPhone,
        rule_type: newRuleType,
        instance_name: isGlobal ? null : instanceName,
      };

      await omniClient.createAccessRule(request);
      setNewPhone('');
      loadRules();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create rule');
    }
  };

  const handleDeleteRule = async (ruleId: number) => {
    if (!confirm('Delete this rule?')) return;

    try {
      await omniClient.deleteAccessRule(ruleId);
      loadRules();
    } catch (err) {
      alert('Failed to delete rule');
    }
  };

  return (
    <div className="access-control-manager">
      <h2>Access Control Rules</h2>

      <div className="create-rule">
        <h3>Create New Rule</h3>
        <input
          type="tel"
          value={newPhone}
          onChange={(e) => setNewPhone(e.target.value)}
          placeholder="+5511999999999 or +5511*"
        />
        <select value={newRuleType} onChange={(e) => setNewRuleType(e.target.value as any)}>
          <option value="allow">Allow</option>
          <option value="block">Block</option>
        </select>
        <label>
          <input
            type="checkbox"
            checked={isGlobal}
            onChange={(e) => setIsGlobal(e.target.checked)}
          />
          Global (all instances)
        </label>
        <button onClick={handleCreateRule}>Create Rule</button>
      </div>

      <div className="rules-list">
        <h3>Existing Rules</h3>
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Phone</th>
                <th>Type</th>
                <th>Scope</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td>{rule.phone_number}</td>
                  <td>
                    <span className={`badge badge-${rule.rule_type}`}>
                      {rule.rule_type}
                    </span>
                  </td>
                  <td>{rule.instance_name || 'Global'}</td>
                  <td>
                    <button onClick={() => handleDeleteRule(rule.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

---

## Best Practices

### 1. API Client Management

```typescript
// ✅ Singleton pattern
export const omniClient = new OmniApiClient();

// ✅ React Context for configuration
export const OmniContext = createContext<OmniApiClient | null>(null);

export function OmniProvider({ children, apiKey, baseURL }: Props) {
  const client = useMemo(
    () => new OmniApiClient(apiKey, baseURL),
    [apiKey, baseURL]
  );

  return <OmniContext.Provider value={client}>{children}</OmniContext.Provider>;
}

export function useOmni() {
  const client = useContext(OmniContext);
  if (!client) throw new Error('useOmni must be within OmniProvider');
  return client;
}
```

### 2. Error Handling

```typescript
// ✅ Typed error handling
interface ApiError {
  statusCode: number;
  message: string;
  details?: any;
}

function handleApiError(error: any): ApiError {
  if (error.response) {
    return {
      statusCode: error.response.status,
      message: error.response.data.detail || 'API error',
      details: error.response.data,
    };
  }

  return {
    statusCode: 500,
    message: error.message || 'Network error',
  };
}

// Usage
try {
  await omniClient.sendText(instance, message);
} catch (err) {
  const apiError = handleApiError(err);

  if (apiError.statusCode === 401) {
    // Redirect to login
  } else if (apiError.statusCode === 403) {
    // Show access denied message
  } else {
    // Show generic error
    console.error(apiError.message);
  }
}
```

### 3. Pagination Helpers

```typescript
// ✅ Reusable pagination hook
export function usePagination<T>(
  fetchFn: (page: number, pageSize: number) => Promise<{ items: T[]; total: number; hasMore: boolean }>,
  pageSize = 50
) {
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadPage = async (newPage: number) => {
    setLoading(true);
    try {
      const result = await fetchFn(newPage, pageSize);
      setItems(result.items);
      setTotal(result.total);
      setHasMore(result.hasMore);
      setPage(newPage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPage(1);
  }, []);

  return {
    items,
    page,
    total,
    hasMore,
    loading,
    nextPage: () => hasMore && loadPage(page + 1),
    prevPage: () => page > 1 && loadPage(page - 1),
    refresh: () => loadPage(page),
  };
}

// Usage
const { items: contacts, loading, nextPage, prevPage } = usePagination(
  (page, pageSize) =>
    omniClient.getContacts('my-bot', { page, page_size: pageSize }),
  50
);
```

### 4. Retry Logic

```typescript
// ✅ Exponential backoff retry
async function fetchWithRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 1000
): Promise<T> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      const isLastAttempt = attempt === maxRetries - 1;
      const isRetryable = error.response?.status >= 500;

      if (isLastAttempt || !isRetryable) {
        throw error;
      }

      const delay = baseDelay * Math.pow(2, attempt);
      console.log(`Retry attempt ${attempt + 1} after ${delay}ms`);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw new Error('Max retries exceeded');
}

// Usage
const instances = await fetchWithRetry(() => omniClient.listInstances());
```

### 5. Caching Strategy

```typescript
// ✅ Simple in-memory cache with TTL
class CacheManager<T> {
  private cache = new Map<string, { data: T; expires: number }>();

  set(key: string, data: T, ttlMs = 60000) {
    this.cache.set(key, {
      data,
      expires: Date.now() + ttlMs,
    });
  }

  get(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    if (Date.now() > entry.expires) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  clear() {
    this.cache.clear();
  }
}

const instanceCache = new CacheManager<Instance[]>();

async function getCachedInstances(): Promise<Instance[]> {
  const cached = instanceCache.get('instances');
  if (cached) return cached;

  const instances = await omniClient.listInstances();
  instanceCache.set('instances', instances, 30000); // 30s TTL
  return instances;
}
```

---

## Error Handling

### Common Error Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 400 | Bad Request | Fix request payload |
| 401 | Unauthorized | Check API key |
| 403 | Forbidden | Check access rules |
| 404 | Not Found | Verify resource exists |
| 422 | Validation Error | Check field values |
| 500 | Server Error | Retry or contact support |

### Error Response Formats

**Standard Error:**
```json
{
  "detail": "Instance 'my-bot' not found"
}
```

**Validation Error (422):**
```json
{
  "detail": [
    {
      "loc": ["body", "phone_number"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Partial Failure (Omni endpoints):**
```json
{
  "contacts": [...],  // Successful data
  "partial_errors": [
    {
      "instance_name": "broken-bot",
      "error": "Connection refused"
    }
  ]
}
```

### Error Handling Patterns

```typescript
// ✅ Comprehensive error handler
function displayError(error: any, context: string) {
  const apiError = handleApiError(error);

  switch (apiError.statusCode) {
    case 400:
      toast.error(`Invalid ${context}: ${apiError.message}`);
      break;
    case 401:
      toast.error('Authentication required');
      router.push('/login');
      break;
    case 403:
      toast.error('Access denied');
      break;
    case 404:
      toast.error(`${context} not found`);
      break;
    case 422:
      toast.error(`Validation error: ${apiError.message}`);
      break;
    case 500:
      toast.error('Server error. Please try again.');
      break;
    default:
      toast.error('An unexpected error occurred');
  }

  // Log for debugging
  console.error(`[${context}]`, apiError);
}

// Usage
try {
  await omniClient.sendText(instance, message);
} catch (err) {
  displayError(err, 'Send message');
}
```

---

## Testing Strategies

### Unit Testing API Client

```typescript
// omni-client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import axios from 'axios';
import { OmniApiClient } from './omni-client';

vi.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('OmniApiClient', () => {
  let client: OmniApiClient;

  beforeEach(() => {
    client = new OmniApiClient('test-key', 'http://localhost:8882');
    mockedAxios.create.mockReturnThis();
  });

  it('should list instances', async () => {
    const mockInstances = [
      { id: 1, name: 'bot1', channel_type: 'whatsapp' },
      { id: 2, name: 'bot2', channel_type: 'discord' },
    ];

    mockedAxios.get.mockResolvedValue({ data: mockInstances });

    const instances = await client.listInstances();
    expect(instances).toEqual(mockInstances);
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/v1/instances', {
      params: { include_status: true },
    });
  });

  it('should handle 401 errors', async () => {
    mockedAxios.get.mockRejectedValue({
      response: { status: 401, data: { detail: 'Invalid API key' } },
    });

    await expect(client.listInstances()).rejects.toThrow();
  });

  it('should send text message', async () => {
    const mockResponse = { success: true, message_id: '123' };
    mockedAxios.post.mockResolvedValue({ data: mockResponse });

    const result = await client.sendText('my-bot', {
      phone_number: '+5511999999999',
      text: 'Hello',
    });

    expect(result).toEqual(mockResponse);
  });
});
```

### Integration Testing

```typescript
// integration.test.ts
import { OmniApiClient } from './omni-client';

describe('Omni API Integration', () => {
  const client = new OmniApiClient(
    process.env.TEST_API_KEY,
    process.env.TEST_API_URL
  );

  it('should create and delete instance', async () => {
    // Create
    const instance = await client.createInstance({
      name: 'test-bot-' + Date.now(),
      channel_type: 'whatsapp',
      evolution_url: 'http://localhost:8080',
      evolution_key: 'test-key',
      agent_api_url: 'http://localhost:8886',
      agent_api_key: 'agent-key',
    });

    expect(instance.name).toBeTruthy();

    // Delete
    await client.deleteInstance(instance.name);

    // Verify deleted
    await expect(client.getInstance(instance.name)).rejects.toThrow();
  });
});
```

### Mocking for Storybook

```typescript
// mocks.ts
export const mockInstances = [
  {
    id: 1,
    name: 'whatsapp-bot',
    channel_type: 'whatsapp' as const,
    evolution_url: 'http://localhost:8080',
    agent_api_url: 'http://localhost:8886',
    is_active: true,
    created_at: '2025-11-04T10:00:00Z',
    evolution_status: {
      state: 'open' as const,
      profile_name: 'Business Bot',
      last_updated: '2025-11-04T12:00:00Z',
    },
  },
  {
    id: 2,
    name: 'discord-bot',
    channel_type: 'discord' as const,
    discord_client_id: '123456789',
    agent_api_url: 'http://localhost:8886',
    is_active: true,
    created_at: '2025-11-03T15:00:00Z',
  },
];

export const mockContacts = {
  contacts: [
    {
      id: '5511999999999@s.whatsapp.net',
      name: 'John Doe',
      channel_type: 'whatsapp' as const,
      instance_name: 'whatsapp-bot',
      status: 'online' as const,
      avatar_url: 'https://example.com/avatar.jpg',
    },
  ],
  total_count: 1,
  page: 1,
  page_size: 50,
  has_more: false,
  instance_name: 'whatsapp-bot',
  channel_type: 'whatsapp' as const,
  partial_errors: [],
};

export const mockAnalytics = {
  total_messages: 1250,
  successful_messages: 1200,
  failed_messages: 50,
  success_rate: 96.0,
  avg_processing_time_ms: 1800.5,
  avg_agent_time_ms: 1500.25,
  message_types: {
    conversation: 1000,
    imageMessage: 150,
    audioMessage: 50,
    documentMessage: 50,
  },
};
```

---

## Appendix: Complete TypeScript SDK

Save this as `omni-sdk.ts` for a production-ready SDK:

```typescript
/**
 * Automagik Omni TypeScript SDK
 * Complete type-safe client for Omni API
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';

// Re-export types (assume they're defined in separate files as shown above)
export * from './types/enums';
export * from './types/instance.types';
export * from './types/omni.types';
export * from './types/messages.types';
export * from './types/access.types';
export * from './types/traces.types';

export interface OmniConfig {
  apiUrl: string;
  apiKey: string;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
}

export class OmniSDK {
  private client: AxiosInstance;
  private config: Required<OmniConfig>;

  constructor(config: OmniConfig) {
    this.config = {
      ...config,
      timeout: config.timeout || 30000,
      retryAttempts: config.retryAttempts || 3,
      retryDelay: config.retryDelay || 1000,
    };

    this.client = axios.create({
      baseURL: this.config.apiUrl,
      timeout: this.config.timeout,
      headers: {
        'x-api-key': this.config.apiKey,
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as AxiosRequestConfig & { _retry?: number };

        // Retry logic for 5xx errors
        if (
          error.response?.status &&
          error.response.status >= 500 &&
          (!config._retry || config._retry < this.config.retryAttempts)
        ) {
          config._retry = (config._retry || 0) + 1;
          const delay = this.config.retryDelay * Math.pow(2, config._retry - 1);

          await new Promise((resolve) => setTimeout(resolve, delay));
          return this.client.request(config);
        }

        return Promise.reject(error);
      }
    );
  }

  // Health
  async health() {
    const { data } = await this.client.get('/health');
    return data;
  }

  // Instances
  get instances() {
    return {
      list: async (params?: { skip?: number; limit?: number; include_status?: boolean }) => {
        const { data } = await this.client.get('/api/v1/instances', { params });
        return data;
      },

      get: async (name: string, includeStatus = true) => {
        const { data } = await this.client.get(`/api/v1/instances/${name}`, {
          params: { include_status: includeStatus },
        });
        return data;
      },

      create: async (config: any) => {
        const { data } = await this.client.post('/api/v1/instances', config);
        return data;
      },

      update: async (name: string, config: any) => {
        const { data } = await this.client.put(`/api/v1/instances/${name}`, config);
        return data;
      },

      delete: async (name: string) => {
        const { data } = await this.client.delete(`/api/v1/instances/${name}`);
        return data;
      },

      qr: async (name: string) => {
        const { data } = await this.client.get(`/api/v1/instances/${name}/qr`);
        return data;
      },

      status: async (name: string) => {
        const { data } = await this.client.get(`/api/v1/instances/${name}/status`);
        return data;
      },

      connect: async (name: string) => {
        const { data } = await this.client.post(`/api/v1/instances/${name}/connect`);
        return data;
      },

      disconnect: async (name: string) => {
        const { data } = await this.client.post(`/api/v1/instances/${name}/disconnect`);
        return data;
      },

      restart: async (name: string) => {
        const { data } = await this.client.post(`/api/v1/instances/${name}/restart`);
        return data;
      },
    };
  }

  // Omni API
  get omni() {
    return {
      contacts: {
        list: async (instanceName: string, params?: any) => {
          const { data } = await this.client.get(
            `/api/v1/instances/${instanceName}/contacts`,
            { params }
          );
          return data;
        },

        get: async (instanceName: string, contactId: string) => {
          const { data } = await this.client.get(
            `/api/v1/instances/${instanceName}/contacts/${contactId}`
          );
          return data;
        },
      },

      chats: {
        list: async (instanceName: string, params?: any) => {
          const { data } = await this.client.get(
            `/api/v1/instances/${instanceName}/chats`,
            { params }
          );
          return data;
        },

        get: async (instanceName: string, chatId: string) => {
          const { data } = await this.client.get(
            `/api/v1/instances/${instanceName}/chats/${chatId}`
          );
          return data;
        },

        messages: async (instanceName: string, chatId: string, params?: any) => {
          const { data } = await this.client.get(
            `/api/v1/instances/${instanceName}/chats/${chatId}/messages`,
            { params }
          );
          return data;
        },
      },
    };
  }

  // Messages
  get messages() {
    return {
      sendText: async (instanceName: string, message: any) => {
        const { data } = await this.client.post(
          `/api/v1/instance/${instanceName}/send-text`,
          message
        );
        return data;
      },

      sendMedia: async (instanceName: string, message: any) => {
        const { data } = await this.client.post(
          `/api/v1/instance/${instanceName}/send-media`,
          message
        );
        return data;
      },

      sendAudio: async (instanceName: string, message: any) => {
        const { data } = await this.client.post(
          `/api/v1/instance/${instanceName}/send-audio`,
          message
        );
        return data;
      },

      sendReaction: async (instanceName: string, message: any) => {
        const { data } = await this.client.post(
          `/api/v1/instance/${instanceName}/send-reaction`,
          message
        );
        return data;
      },
    };
  }

  // Access Control
  get access() {
    return {
      list: async (filters?: any) => {
        const { data } = await this.client.get('/api/v1/access/rules', {
          params: filters,
        });
        return data;
      },

      create: async (rule: any) => {
        const { data } = await this.client.post('/api/v1/access/rules', rule);
        return data;
      },

      delete: async (ruleId: number) => {
        await this.client.delete(`/api/v1/access/rules/${ruleId}`);
      },
    };
  }

  // Traces & Analytics
  get traces() {
    return {
      list: async (filters?: any) => {
        const { data } = await this.client.get('/api/v1/traces', {
          params: filters,
        });
        return data;
      },

      get: async (traceId: string) => {
        const { data } = await this.client.get(`/api/v1/traces/${traceId}`);
        return data;
      },

      payloads: async (traceId: string, includePayload = false) => {
        const { data } = await this.client.get(`/api/v1/traces/${traceId}/payloads`, {
          params: { include_payload: includePayload },
        });
        return data;
      },

      analytics: async (filters?: any) => {
        const { data} = await this.client.get('/api/v1/traces/analytics/summary', {
          params: filters,
        });
        return data;
      },
    };
  }
}

// Convenience export
export function createOmniClient(config: OmniConfig): OmniSDK {
  return new OmniSDK(config);
}
```

---

## Summary

This guide provides everything you need to build production-ready frontends for Automagik Omni:

✅ **Quick Start** - Get running in minutes
✅ **Complete API Reference** - All endpoints documented
✅ **TypeScript Types** - Full type safety
✅ **Real Examples** - Copy-paste React components
✅ **Best Practices** - Error handling, caching, retries
✅ **Testing** - Unit, integration, and mocks
✅ **Production SDK** - Battle-tested client library

### Next Steps

1. **Set up your environment** - Install dependencies, configure API key
2. **Create API client** - Use provided SDK or build your own
3. **Build core features** - Instances, messages, contacts, chats
4. **Add analytics** - Traces and performance monitoring
5. **Implement access control** - Phone number rules
6. **Test thoroughly** - Use provided testing strategies
7. **Deploy** - Follow security best practices

### Getting Help

- **Documentation**: This guide + inline API comments
- **OpenAPI Spec**: `http://localhost:8882/api/v1/docs`
- **Health Check**: `http://localhost:8882/health`
- **GitHub Issues**: Report bugs and request features

---

**Document Version:** 1.0
**Last Updated:** 2025-11-04
**API Version:** v1
**License:** Proprietary - Namastex Labs

