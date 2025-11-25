import { User, Users } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface ChatListItemProps {
  chat: any;
  isSelected: boolean;
  onClick: () => void;
}

export function ChatListItem({ chat, isSelected, onClick }: ChatListItemProps) {
  const name = chat.name || chat.pushName || formatJid(chat.remoteJid);
  const isGroup = chat.remoteJid?.includes('@g.us') || chat.isGroup;
  const unreadCount = chat.unreadCount || 0;
  const lastMessage = getLastMessagePreview(chat);
  const timestamp = formatTimestamp(chat.lastMessageTimestamp || chat.updatedAt);

  return (
    <div
      className={cn(
        'flex items-center gap-3 p-3 cursor-pointer transition-colors hover:bg-muted/50',
        isSelected && 'bg-muted'
      )}
      onClick={onClick}
    >
      <Avatar className="h-12 w-12 flex-shrink-0">
        <AvatarImage src={chat.profilePictureUrl} />
        <AvatarFallback>
          {isGroup ? <Users className="h-5 w-5" /> : <User className="h-5 w-5" />}
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium truncate">{name}</span>
          {timestamp && (
            <span className="text-xs text-muted-foreground flex-shrink-0">
              {timestamp}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 mt-0.5">
          <p className="text-sm text-muted-foreground truncate">
            {lastMessage || 'No messages'}
          </p>
          {unreadCount > 0 && (
            <Badge
              variant="default"
              className="bg-green-500 text-white h-5 min-w-5 flex items-center justify-center rounded-full px-1.5"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
        </div>
      </div>
    </div>
  );
}

function formatJid(jid: string | undefined): string {
  if (!jid) return 'Unknown';
  // Remove @s.whatsapp.net or @g.us suffix
  return jid.split('@')[0];
}

function getLastMessagePreview(chat: any): string {
  const msg = chat.lastMessage;
  if (!msg) return '';

  if (msg.message?.conversation) return msg.message.conversation;
  if (msg.message?.extendedTextMessage?.text) return msg.message.extendedTextMessage.text;
  if (msg.message?.imageMessage) return '📷 Photo';
  if (msg.message?.videoMessage) return '🎥 Video';
  if (msg.message?.audioMessage) return '🎵 Audio';
  if (msg.message?.documentMessage) return '📄 Document';
  if (msg.message?.stickerMessage) return '🎨 Sticker';
  if (msg.message?.contactMessage) return '👤 Contact';
  if (msg.message?.locationMessage) return '📍 Location';

  return '';
}

function formatTimestamp(timestamp: number | string | undefined): string {
  if (!timestamp) return '';

  const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // Today
  if (diff < 86400000 && date.getDate() === now.getDate()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Yesterday
  if (diff < 172800000) {
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.getDate() === yesterday.getDate()) {
      return 'Yesterday';
    }
  }

  // This week
  if (diff < 604800000) {
    return date.toLocaleDateString([], { weekday: 'short' });
  }

  // Older
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}
