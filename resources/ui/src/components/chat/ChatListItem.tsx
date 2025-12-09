import { User, Users } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib';
import type { EvolutionChat, EvolutionMessage } from '@/lib';

interface ChatListItemProps {
  chat: EvolutionChat;
  isSelected: boolean;
  onClick: () => void;
}

export function ChatListItem({ chat, isSelected, onClick }: ChatListItemProps) {
  // Use the merged name from ChatLayout, fallback to pushName or formatted JID
  const name = chat.name || chat.pushName || formatJid(chat.remoteJid);
  const isGroup = chat.isGroup || chat.remoteJid?.includes('@g.us');
  const unreadCount = chat.unreadCount || 0;
  const lastMessage = getLastMessagePreview(chat);
  const timestamp = formatTimestamp(chat.lastMessageTimestamp || chat.updatedAt);
  const avatarUrl = chat.profilePicUrl || chat.profilePictureUrl || chat.pictureUrl;

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-3 py-3 cursor-pointer transition-colors',
        'hover:bg-accent/50',
        isSelected && 'bg-accent'
      )}
      onClick={onClick}
    >
      <Avatar className="h-12 w-12 flex-shrink-0">
        <AvatarImage src={avatarUrl} />
        <AvatarFallback className="bg-primary/20 text-primary">
          {isGroup ? (
            <Users className="h-6 w-6" />
          ) : (
            <span className="text-lg font-medium">
              {name.charAt(0).toUpperCase()}
            </span>
          )}
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 min-w-0 border-b border-border py-2 -my-2 -mr-3 pr-3">
        <div className="flex items-center justify-between gap-2">
          <span className="font-medium truncate text-foreground">
            {name}
          </span>
          {timestamp && (
            <span className={cn(
              'text-xs flex-shrink-0',
              unreadCount > 0 ? 'text-primary font-medium' : 'text-muted-foreground'
            )}>
              {timestamp}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 mt-0.5">
          <p className="text-sm text-muted-foreground truncate">
            {lastMessage || (isGroup ? 'Group chat' : 'Click to open')}
          </p>
          {unreadCount > 0 && (
            <span className="bg-primary text-primary-foreground text-xs font-medium h-5 min-w-5 flex items-center justify-center rounded-full px-1.5">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function formatJid(jid: string | undefined): string {
  if (!jid) return 'Unknown';
  const id = jid.split('@')[0];

  // Format as phone number if possible
  if (jid.includes('@s.whatsapp.net') && id.length >= 10) {
    return `+${id}`;
  }

  return id;
}

function getLastMessagePreview(chat: EvolutionChat): string {
  const msg = chat.lastMessage as EvolutionMessage | undefined;
  if (!msg) return '';

  if (msg.message?.conversation) return msg.message.conversation;
  if (msg.message?.extendedTextMessage?.text) return msg.message.extendedTextMessage.text;
  if (msg.message?.imageMessage) return '📷 Photo';
  if (msg.message?.videoMessage) return '🎥 Video';
  if (msg.message?.audioMessage) return msg.message.audioMessage.ptt ? '🎤 Voice message' : '🎵 Audio';
  if (msg.message?.documentMessage) return `📄 ${msg.message.documentMessage.fileName || 'Document'}`;
  if (msg.message?.stickerMessage) return '🎨 Sticker';
  if (msg.message?.contactMessage) return `👤 ${msg.message.contactMessage.displayName || 'Contact'}`;
  if (msg.message?.locationMessage) return '📍 Location';
  if (msg.message?.reactionMessage) return `Reacted ${msg.message.reactionMessage.text}`;

  return '';
}

function formatTimestamp(timestamp: number | string | undefined): string {
  if (!timestamp) return '';

  const date = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // Today - show time
  if (diff < 86400000 && date.getDate() === now.getDate()) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  // Yesterday
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.getDate() === yesterday.getDate() &&
      date.getMonth() === yesterday.getMonth() &&
      date.getFullYear() === yesterday.getFullYear()) {
    return 'Yesterday';
  }

  // This week - show day name
  if (diff < 604800000) {
    return date.toLocaleDateString([], { weekday: 'long' });
  }

  // Older - show date
  return date.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' });
}
