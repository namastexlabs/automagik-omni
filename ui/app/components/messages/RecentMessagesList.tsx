import { Badge } from '@/app/components/ui/badge'
import type { Message } from '@/lib/conveyor/schemas/omni-schema'

interface RecentMessagesListProps {
  messages: Message[]
}

export function RecentMessagesList({ messages }: RecentMessagesListProps) {
  if (messages.length === 0) {
    return (
      <div className="text-center py-8 text-zinc-500">
        No messages sent yet
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {messages.map((message) => (
        <div
          key={message.id}
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-4"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant="outline" className="text-xs">
                  {message.message_type}
                </Badge>
                <Badge variant={message.status === 'sent' ? 'default' : 'destructive'} className="text-xs">
                  {message.status}
                </Badge>
              </div>
              <p className="text-sm text-zinc-400 truncate">To: {message.to}</p>
            </div>
            <p className="text-xs text-zinc-500 ml-2">
              {new Date(message.timestamp).toLocaleTimeString()}
            </p>
          </div>
          <p className="text-sm break-words">{message.content}</p>
        </div>
      ))}
    </div>
  )
}
