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
