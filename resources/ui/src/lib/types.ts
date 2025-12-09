// Instance Configuration Types
export interface InstanceConfig {
  id?: number;
  name: string;
  channel_type: 'whatsapp' | 'discord' | 'slack';
  is_default?: boolean;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;

  // WhatsApp specific (Evolution API)
  whatsapp_instance?: string;
  evolution_url?: string;
  evolution_key?: string;
  session_id_prefix?: string;
  webhook_base64?: boolean;

  // Discord specific
  has_discord_bot_token?: boolean;
  discord_client_id?: string | null;
  discord_guild_id?: string | null;
  discord_default_channel_id?: string | null;
  discord_voice_enabled?: boolean;
  discord_slash_commands_enabled?: boolean;

  // Agent configuration
  agent_api_url?: string;
  agent_api_key?: string;
  default_agent?: string;
  agent_timeout?: number;
  agent_instance_type?: string;
  agent_id?: string;
  agent_type?: string;
  agent_stream_mode?: boolean;

  // Automagik integration
  automagik_instance_id?: string | null;
  automagik_instance_name?: string | null;

  // Profile information
  profile_name?: string | null;
  profile_pic_url?: string | null;
  owner_jid?: string | null;

  // Evolution status (runtime data)
  evolution_status?: {
    state?: string;
    owner_jid?: string | null;
    profile_name?: string | null;
    profile_picture_url?: string | null;
    last_updated?: string;
    error?: string | null;
  };

  // Additional features
  enable_auto_split?: boolean;
}

export interface InstanceCreateRequest {
  name: string;
  channel_type: 'whatsapp' | 'discord' | 'slack';
  is_default?: boolean;

  // WhatsApp specific
  whatsapp_instance?: string;
  evolution_url?: string;
  evolution_key?: string;

  // Discord specific
  discord_client_id?: string;
  discord_guild_id?: string;
  discord_bot_token?: string;

  // Agent configuration
  agent_api_url?: string;
  agent_api_key?: string;
  default_agent?: string;
}

export interface InstanceUpdateRequest {
  name?: string;
  is_default?: boolean;
  is_active?: boolean;

  // WhatsApp specific
  whatsapp_instance?: string;
  evolution_url?: string;
  evolution_key?: string;

  // Discord specific
  discord_client_id?: string;
  discord_guild_id?: string;
  discord_bot_token?: string;

  // Agent configuration
  agent_api_url?: string;
  agent_api_key?: string;
  default_agent?: string;
}

// Contact Types
export type OmniContactStatus = 'available' | 'unavailable' | 'composing' | 'recording' | 'paused';

export interface OmniContact {
  id: string;
  instance_name: string;
  contact_id: string;
  name?: string;
  phone_number?: string;
  profile_picture_url?: string;
  status?: OmniContactStatus;
  status_message?: string;
  is_business?: boolean;
  is_enterprise?: boolean;
  last_seen?: string;
  created_at?: string;
  updated_at?: string;
}

// Chat Types
export type OmniChatType = 'direct' | 'group' | 'channel' | 'thread';

export interface OmniChat {
  id: string;
  instance_name: string;
  chat_id: string;
  chat_type: OmniChatType;
  name?: string;
  description?: string;
  profile_picture_url?: string;
  is_archived?: boolean;
  is_pinned?: boolean;
  unread_count?: number;
  last_message?: string;
  last_message_timestamp?: string;
  participant_count?: number;
  created_at?: string;
  updated_at?: string;
}

// API Response Types
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Evolution API Types

export interface EvolutionSettings {
  rejectCall: boolean;
  msgCall: string;
  groupsIgnore: boolean;
  alwaysOnline: boolean;
  readMessages: boolean;
  readStatus: boolean;
  syncFullHistory: boolean;
}

export interface EvolutionWebhookConfig {
  enabled: boolean;
  url: string;
  headers?: Record<string, string>;
  byEvents: boolean;
  base64: boolean;
  events: string[];
}

export interface EvolutionWebSocketConfig {
  enabled: boolean;
  events: string[];
}

export interface EvolutionRabbitMQConfig {
  enabled: boolean;
  uri?: string;
  exchange?: string;
  events: string[];
}

export interface EvolutionConnectionState {
  instance: string;
  state: 'open' | 'close' | 'connecting' | 'refused';
}

export interface EvolutionProfile {
  name?: string;
  status?: string;
  pictureUrl?: string;
  jid?: string;
  phone?: string;
}

export interface EvolutionStats {
  contacts?: number;
  chats?: number;
  messages?: number;
}

export interface EvolutionMessage {
  key: {
    remoteJid: string;
    fromMe: boolean;
    id: string;
  };
  pushName?: string;
  message?: {
    conversation?: string;
    extendedTextMessage?: { text: string };
    imageMessage?: { caption?: string; mimetype?: string; url?: string };
    videoMessage?: { caption?: string; mimetype?: string; url?: string };
    audioMessage?: { mimetype?: string; url?: string };
    documentMessage?: { fileName?: string; mimetype?: string; url?: string };
  };
  messageType?: string;
  messageTimestamp?: number;
  status?: 'PENDING' | 'SENT' | 'DELIVERED' | 'READ' | 'PLAYED';
}

export interface EvolutionChat {
  id: string;
  remoteJid: string;
  name?: string;
  profilePictureUrl?: string;
  unreadCount?: number;
  lastMessage?: EvolutionMessage;
  lastMessageTimestamp?: number;
  isGroup?: boolean;
}

export interface EvolutionContact {
  id: string;
  remoteJid: string;
  pushName?: string;
  profilePictureUrl?: string;
  phone?: string;
}

// Event types for webhook/websocket configuration
export const EVOLUTION_EVENTS = [
  'APPLICATION_STARTUP',
  'QRCODE_UPDATED',
  'MESSAGES_SET',
  'MESSAGES_UPSERT',
  'MESSAGES_UPDATE',
  'MESSAGES_DELETE',
  'SEND_MESSAGE',
  'CONTACTS_SET',
  'CONTACTS_UPSERT',
  'CONTACTS_UPDATE',
  'CHATS_SET',
  'CHATS_UPSERT',
  'CHATS_UPDATE',
  'CHATS_DELETE',
  'GROUPS_UPSERT',
  'GROUPS_UPDATE',
  'PRESENCE_UPDATE',
  'CONNECTION_UPDATE',
  'CALL',
  'LABELS_EDIT',
  'LABELS_ASSOCIATION',
  'LOGOUT_INSTANCE',
  'REMOVE_INSTANCE',
] as const;

export type EvolutionEventType = (typeof EVOLUTION_EVENTS)[number];

// Global Settings Types
export type SettingValueType = 'string' | 'integer' | 'boolean' | 'json' | 'secret';

export interface GlobalSetting {
  id: number;
  key: string;
  value: string | null;
  value_type: SettingValueType;
  category?: string;
  description?: string;
  is_secret: boolean;
  is_required: boolean;
  default_value?: string;
  validation_rules?: string;
  created_at: string;
  updated_at: string;
  created_by?: string;
  updated_by?: string;
}

export interface SettingCreateRequest {
  key: string;
  value: string;
  value_type: SettingValueType;
  category?: string;
  description?: string;
  is_secret?: boolean;
  is_required?: boolean;
  default_value?: string;
  validation_rules?: Record<string, unknown>;
}

export interface SettingUpdateRequest {
  value: string;
  updated_by?: string;
  change_reason?: string;
}

export interface SettingChangeHistory {
  id: number;
  setting_id: number;
  old_value?: string;
  new_value?: string;
  changed_by?: string;
  changed_at: string;
  change_reason?: string;
}

export interface SettingEntry {
  key: string;
  value: string | number | boolean | null;
  value_type?: SettingValueType;
  category?: string;
  description?: string;
  is_secret?: boolean;
  is_required?: boolean;
  default_value?: string | null;
  validation_rules?: Record<string, unknown> | string | null;
  updated_at?: string;
}

export type ActionResponse = {
  success?: boolean;
  message?: string;
  status?: string;
};

export interface InstanceStatusResponse {
  status: 'connected' | 'disconnected' | 'pending' | 'unknown' | string;
  message?: string;
  evolution_status?: InstanceConfig['evolution_status'];
}

export interface GatewayProcessInfo {
  port: number;
  healthy: boolean;
  pid?: number;
}

export interface GatewayStatus {
  gateway: {
    port: number;
    mode: string;
    proxyOnly: boolean;
    lazyChannels: boolean;
    uptime: number;
  };
  ports: Record<string, number>;
  processes: Record<string, GatewayProcessInfo>;
}

export interface EvolutionGroup {
  id: string;
  subject?: string;
  pictureUrl?: string;
}

export interface EvolutionMessage {
  key?: {
    id?: string;
    remoteJid?: string;
    fromMe?: boolean;
  };
  message?: {
    conversation?: string;
    extendedTextMessage?: { text?: string };
    imageMessage?: { caption?: string; jpegThumbnail?: string };
    videoMessage?: { caption?: string; jpegThumbnail?: string };
    audioMessage?: { ptt?: boolean };
    documentMessage?: { fileName?: string };
    stickerMessage?: unknown;
    contactMessage?: { displayName?: string };
    locationMessage?: unknown;
    reactionMessage?: { text?: string };
  };
  messageTimestamp?: number | string;
}

export interface EvolutionChat {
  id?: string;
  remoteJid: string;
  name?: string;
  pushName?: string;
  isGroup?: boolean;
  unreadCount?: number;
  lastMessage?: EvolutionMessage;
  lastMessageTimestamp?: number | string;
  updatedAt?: number | string;
  profilePicUrl?: string;
  profilePictureUrl?: string;
  pictureUrl?: string;
}

export interface EvolutionContact {
  id?: string;
  remoteJid?: string;
  name?: string;
  pushName?: string;
  profilePicUrl?: string;
  profilePictureUrl?: string;
}

export interface SettingHistoryEntry {
  id?: number;
  value: string | number | boolean | null;
  updated_at?: string;
  updated_by?: string;
  change_reason?: string | null;
}
