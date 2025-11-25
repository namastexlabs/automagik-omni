import { Check, CheckCheck, Clock, User } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  message: any;
  showAvatar?: boolean;
}

export function MessageBubble({ message, showAvatar = false }: MessageBubbleProps) {
  const isFromMe = message.key?.fromMe;
  const content = getMessageContent(message);
  const timestamp = formatMessageTime(message.messageTimestamp);
  const status = message.status;
  const senderName = message.pushName;

  return (
    <div
      className={cn(
        'flex gap-2',
        isFromMe ? 'justify-end' : 'justify-start'
      )}
    >
      {/* Avatar for group messages (not from me) */}
      {showAvatar && !isFromMe && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarFallback>
            <User className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          'max-w-[70%] rounded-lg px-3 py-2',
          isFromMe
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        {/* Sender name in groups */}
        {showAvatar && !isFromMe && senderName && (
          <p className="text-xs font-medium mb-1 opacity-70">
            {senderName}
          </p>
        )}

        {/* Media content */}
        {content.type !== 'text' && (
          <div className="mb-1">
            {content.type === 'image' && (
              <img
                src={content.url}
                alt="Image"
                className="rounded max-w-full max-h-64 object-contain"
              />
            )}
            {content.type === 'video' && (
              <video
                src={content.url}
                controls
                className="rounded max-w-full max-h-64"
              />
            )}
            {content.type === 'audio' && (
              <audio src={content.url} controls className="max-w-full" />
            )}
            {content.type === 'document' && (
              <div className="flex items-center gap-2 p-2 rounded bg-background/50">
                <span>📄</span>
                <span className="text-sm truncate">{content.filename}</span>
              </div>
            )}
            {content.type === 'sticker' && (
              <img
                src={content.url}
                alt="Sticker"
                className="w-32 h-32 object-contain"
              />
            )}
          </div>
        )}

        {/* Text content */}
        {content.text && (
          <p className="text-sm whitespace-pre-wrap break-words">
            {content.text}
          </p>
        )}

        {/* Timestamp and status */}
        <div
          className={cn(
            'flex items-center gap-1 mt-1',
            isFromMe ? 'justify-end' : 'justify-start'
          )}
        >
          <span className="text-[10px] opacity-60">{timestamp}</span>
          {isFromMe && <StatusIcon status={status} />}
        </div>
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status?: string }) {
  switch (status) {
    case 'PENDING':
      return <Clock className="h-3 w-3 opacity-60" />;
    case 'SENT':
      return <Check className="h-3 w-3 opacity-60" />;
    case 'DELIVERED':
      return <CheckCheck className="h-3 w-3 opacity-60" />;
    case 'READ':
    case 'PLAYED':
      return <CheckCheck className="h-3 w-3 text-blue-400" />;
    default:
      return <Check className="h-3 w-3 opacity-60" />;
  }
}

interface MessageContent {
  type: 'text' | 'image' | 'video' | 'audio' | 'document' | 'sticker' | 'location' | 'contact';
  text?: string;
  url?: string;
  filename?: string;
}

function getMessageContent(message: any): MessageContent {
  const msg = message.message || {};

  if (msg.conversation) {
    return { type: 'text', text: msg.conversation };
  }
  if (msg.extendedTextMessage?.text) {
    return { type: 'text', text: msg.extendedTextMessage.text };
  }
  if (msg.imageMessage) {
    return {
      type: 'image',
      text: msg.imageMessage.caption,
      url: msg.imageMessage.url,
    };
  }
  if (msg.videoMessage) {
    return {
      type: 'video',
      text: msg.videoMessage.caption,
      url: msg.videoMessage.url,
    };
  }
  if (msg.audioMessage) {
    return {
      type: 'audio',
      url: msg.audioMessage.url,
    };
  }
  if (msg.documentMessage) {
    return {
      type: 'document',
      filename: msg.documentMessage.fileName,
      url: msg.documentMessage.url,
    };
  }
  if (msg.stickerMessage) {
    return {
      type: 'sticker',
      url: msg.stickerMessage.url,
    };
  }
  if (msg.locationMessage) {
    return {
      type: 'location',
      text: `📍 Location: ${msg.locationMessage.degreesLatitude}, ${msg.locationMessage.degreesLongitude}`,
    };
  }
  if (msg.contactMessage) {
    return {
      type: 'contact',
      text: `👤 Contact: ${msg.contactMessage.displayName}`,
    };
  }

  return { type: 'text', text: '[Unsupported message type]' };
}

function formatMessageTime(timestamp: number | undefined): string {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
