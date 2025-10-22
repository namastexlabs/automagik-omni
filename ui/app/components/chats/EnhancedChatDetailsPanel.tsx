import { useEffect, useState, useRef } from 'react'
import { Badge } from '@/app/components/ui/badge'
import type { Chat, Message } from '@/lib/conveyor/schemas/omni-schema'
import { FileIcon, DownloadIcon, PlayIcon, ImageIcon } from 'lucide-react'
import { useConveyor } from '@/app/hooks/use-conveyor'

interface EnhancedChatDetailsPanelProps {
  chat: Chat | null
  onClose: () => void
  instanceName: string
}

interface MessageItemProps {
  message: Message
}

function MessageItem({ message }: MessageItemProps) {
  const renderMedia = () => {
    switch (message.message_type) {
      case 'image':
        return (
          <div className="mb-2">
            <img
              src={message.media_url || ''}
              alt={message.caption || 'Image'}
              className="max-w-sm rounded-lg shadow-lg cursor-pointer hover:opacity-90 transition-opacity"
              onClick={() => window.open(message.media_url || '', '_blank')}
            />
            {message.caption && (
              <p className="text-sm mt-1 text-zinc-300">{message.caption}</p>
            )}
          </div>
        )

      case 'video':
        return (
          <div className="mb-2">
            <video
              controls
              className="max-w-sm rounded-lg shadow-lg"
              poster={message.thumbnail_url || undefined}
            >
              <source src={message.media_url || ''} type={message.media_mime_type || 'video/mp4'} />
              Your browser does not support the video tag.
            </video>
            {message.caption && (
              <p className="text-sm mt-1 text-zinc-300">{message.caption}</p>
            )}
          </div>
        )

      case 'audio':
        return (
          <div className="mb-2">
            <audio controls className="w-full max-w-sm">
              <source src={message.media_url || ''} type={message.media_mime_type || 'audio/mpeg'} />
              Your browser does not support the audio element.
            </audio>
          </div>
        )

      case 'document':
        return (
          <a
            href={message.media_url || ''}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center space-x-2 px-3 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg transition-colors mb-2"
          >
            <FileIcon className="w-5 h-5 text-zinc-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {message.caption || 'Document'}
              </p>
              {message.media_size && (
                <p className="text-xs text-zinc-400">
                  {(message.media_size / 1024).toFixed(1)} KB
                </p>
              )}
            </div>
            <DownloadIcon className="w-4 h-4 text-zinc-400" />
          </a>
        )

      case 'sticker':
        return (
          <div className="mb-2">
            <img
              src={message.media_url || ''}
              alt="Sticker"
              className="w-32 h-32 object-contain"
            />
          </div>
        )

      default:
        return null
    }
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div
      className={`flex mb-3 ${message.is_from_me ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[70%] rounded-lg p-3 ${
          message.is_from_me
            ? 'bg-blue-600 text-white'
            : 'bg-zinc-800 text-white'
        }`}
      >
        {/* Sender name for incoming messages */}
        {!message.is_from_me && message.sender_name && (
          <div className="text-xs font-semibold text-zinc-400 mb-1">
            {message.sender_name}
          </div>
        )}

        {/* Reply indicator */}
        {message.is_reply && (
          <div className="text-xs text-zinc-400 mb-1 pl-2 border-l-2 border-zinc-500">
            Replying to a message
          </div>
        )}

        {/* Forward indicator */}
        {message.is_forwarded && (
          <div className="text-xs italic text-zinc-400 mb-1">
            Forwarded
          </div>
        )}

        {/* Media content */}
        {renderMedia()}

        {/* Text content */}
        {message.text && (
          <div className="text-sm whitespace-pre-wrap break-words">
            {message.text}
          </div>
        )}

        {/* Message type indicator for special messages */}
        {['contact', 'location', 'reaction', 'system'].includes(message.message_type) && (
          <div className="text-xs text-zinc-400 italic">
            [{message.message_type}]
          </div>
        )}

        {/* Timestamp and edited indicator */}
        <div className="flex items-center justify-end space-x-2 mt-1">
          {message.edited_at && (
            <span className="text-xs text-zinc-400">edited</span>
          )}
          <span className="text-xs text-zinc-400">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    </div>
  )
}

export function EnhancedChatDetailsPanel({
  chat,
  onClose,
  instanceName,
}: EnhancedChatDetailsPanelProps) {
  const { omni } = useConveyor()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchMessages = async (pageNum: number = 1) => {
    if (!chat) return

    setLoading(true)
    setError(null)

    try {
      const result = await omni.listMessages(instanceName, chat.id, pageNum, 50)

      if (pageNum === 1) {
        setMessages(result.messages || [])
        scrollToBottom()
      } else {
        setMessages((prev) => [...prev, ...(result.messages || [])])
      }

      setHasMore(result.has_more || false)
      setPage(pageNum)
    } catch (err) {
      console.error('Error fetching messages:', err)
      setError(err instanceof Error ? err.message : 'Failed to load messages')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (chat) {
      fetchMessages(1)
    } else {
      setMessages([])
      setPage(1)
      setHasMore(false)
      setError(null)
    }
  }, [chat?.id])

  if (!chat) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-2/3 lg:w-1/2 bg-zinc-950 border-l border-zinc-800 flex flex-col z-50 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-2xl">
            {chat.chat_type === 'group' ? '👥' : chat.chat_type === 'channel' ? '📢' : '💬'}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">{chat.name || 'Unknown'}</h2>
            <p className="text-xs text-zinc-400">
              {chat.channel_type} • {chat.chat_type}
              {chat.unread_count && chat.unread_count > 0 ? ` • ${chat.unread_count} unread` : ''}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-zinc-400 hover:text-white text-3xl leading-none p-2 hover:bg-zinc-800 rounded transition-colors"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1 bg-zinc-950">
        {loading && page === 1 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
              <p className="text-zinc-400 text-sm">Loading messages...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center p-4 bg-red-900/20 border border-red-900 rounded-lg">
              <p className="text-red-400">{error}</p>
              <button
                onClick={() => fetchMessages(1)}
                className="mt-2 text-sm text-blue-400 hover:text-blue-300 underline"
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {!loading && !error && messages.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-zinc-500">
              <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No messages yet</p>
            </div>
          </div>
        )}

        {!loading && messages.length > 0 && (
          <>
            {hasMore && (
              <div className="text-center mb-4">
                <button
                  onClick={() => fetchMessages(page + 1)}
                  disabled={loading}
                  className="text-sm text-blue-400 hover:text-blue-300 underline disabled:opacity-50"
                >
                  {loading ? 'Loading...' : 'Load more messages'}
                </button>
              </div>
            )}

            {messages.map((message) => (
              <MessageItem key={message.id} message={message} />
            ))}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Footer with metadata */}
      <div className="p-4 border-t border-zinc-800 bg-zinc-900">
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-zinc-400">Status:</span>
            <Badge variant={chat.is_archived ? 'destructive' : 'default'} className="ml-2">
              {chat.is_archived ? 'Archived' : 'Active'}
            </Badge>
          </div>
          {chat.participant_count && (
            <div>
              <span className="text-zinc-400">Participants:</span>
              <span className="ml-2 text-white">{chat.participant_count}</span>
            </div>
          )}
          {chat.last_message_at && (
            <div className="col-span-2">
              <span className="text-zinc-400">Last activity:</span>
              <span className="ml-2 text-white">
                {new Date(chat.last_message_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
