// Re-export types from store for convenience
export type { Instance, AppState } from '../store/app-store'

// Additional shared types for the application
export interface ApiResponse<T> {
  data: T
  error?: string
  message?: string
}

export interface PaginationParams {
  page?: number
  pageSize?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

// Common status types
export type InstanceStatus = 'connected' | 'disconnected' | 'connecting' | 'error'
export type ChannelType = 'whatsapp' | 'discord' | 'telegram' | 'slack'

// Extended instance type with more details
export interface InstanceDetails {
  name: string
  channelType: ChannelType
  status: InstanceStatus
  isDefault?: boolean
  createdAt?: string
  updatedAt?: string
  config?: Record<string, unknown>
}

// Message types
export interface Message {
  id: string
  instanceName: string
  channelType: ChannelType
  content: string
  sender: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// Contact types
export interface Contact {
  id: string
  name?: string
  phoneNumber?: string
  username?: string
  avatar?: string
  lastSeen?: string
}

// Chat types
export interface Chat {
  id: string
  name: string
  type: 'direct' | 'group' | 'channel'
  lastMessage?: string
  lastMessageTime?: string
  unreadCount?: number
  participants?: Contact[]
}
