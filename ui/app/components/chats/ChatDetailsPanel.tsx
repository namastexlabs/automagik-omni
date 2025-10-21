import { Badge } from '@/app/components/ui/badge'
import type { Chat } from '@/lib/main/omni-api-client'

interface ChatDetailsPanelProps {
  chat: Chat | null
  onClose: () => void
}

export function ChatDetailsPanel({ chat, onClose }: ChatDetailsPanelProps) {
  if (!chat) return null

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-zinc-950 border-l border-zinc-800 p-6 overflow-auto z-50">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white">Chat Details</h2>
        <button
          onClick={onClose}
          className="text-zinc-400 hover:text-white text-2xl leading-none"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div className="space-y-6">
        {/* Chat Icon */}
        <div className="flex justify-center">
          <div className="w-24 h-24 rounded-full bg-zinc-800 flex items-center justify-center text-4xl text-zinc-400">
            {chat.chat_type === 'group' ? '👥' : chat.chat_type === 'channel' ? '📢' : '💬'}
          </div>
        </div>

        {/* Name */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">Name</label>
          <p className="text-white">{chat.name || 'Unknown'}</p>
        </div>

        {/* Chat Type */}
        {chat.chat_type && (
          <div>
            <label className="text-sm text-zinc-400 block mb-1">Type</label>
            <Badge variant="default">{chat.chat_type}</Badge>
          </div>
        )}

        {/* Unread Count */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">Unread Messages</label>
          <p className="text-white">{chat.unread_count || 0}</p>
        </div>

        {/* Last Message */}
        {chat.last_message_text && (
          <div>
            <label className="text-sm text-zinc-400 block mb-1">Last Message</label>
            <p className="text-white text-sm">{chat.last_message_text}</p>
          </div>
        )}

        {/* Last Message Timestamp */}
        {chat.last_message_time && (
          <div>
            <label className="text-sm text-zinc-400 block mb-1">Last Activity</label>
            <p className="text-white text-sm">
              {new Date(chat.last_message_time).toLocaleString()}
            </p>
          </div>
        )}

        {/* Archived Status */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">Status</label>
          <Badge variant={chat.archived ? 'destructive' : 'default'}>
            {chat.archived ? 'Archived' : 'Active'}
          </Badge>
        </div>

        {/* Channel Type */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">Channel</label>
          <Badge variant="default">{chat.channel_type}</Badge>
        </div>

        {/* Chat ID */}
        <div>
          <label className="text-sm text-zinc-400 block mb-1">ID</label>
          <p className="text-xs text-zinc-500 font-mono break-all">{chat.chat_id}</p>
        </div>
      </div>
    </div>
  )
}
