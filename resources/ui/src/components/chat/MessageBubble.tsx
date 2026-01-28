import { useState, useEffect, useRef } from 'react';
import { Check, CheckCheck, Clock, User, Play, Pause, Mic, Download, FileText, Image as ImageIcon } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn, api, formatTimeFromTimestamp } from '@/lib';
import type { OmniMessage, OmniMessageReaction, OmniMediaContent, EvolutionMessage } from '@/lib';

interface MessageBubbleProps {
  message: OmniMessage;
  instanceName: string;
  showAvatar?: boolean;
}

// Group reactions by emoji and count
function groupReactionsByEmoji(reactions: OmniMessageReaction[]): Record<string, OmniMessageReaction[]> {
  return reactions.reduce(
    (acc, r) => {
      const emoji = r.emoji;
      if (!acc[emoji]) acc[emoji] = [];
      acc[emoji].push(r);
      return acc;
    },
    {} as Record<string, OmniMessageReaction[]>,
  );
}

// Render text with highlighted @mentions
function TextWithMentions({ text, className }: { text: string; className?: string }) {
  // Match @mentions (word characters, spaces in names, or phone numbers with +)
  const mentionRegex = /(@[\w\s+]+?)(?=\s|$|[.,!?;:])/g;

  const parts: (string | JSX.Element)[] = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionRegex.exec(text)) !== null) {
    // Add text before the mention
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    // Add the styled mention
    parts.push(
      <span key={match.index} className="font-semibold text-primary">
        {match[0]}
      </span>,
    );
    lastIndex = match.index + match[0].length;
  }

  // Add remaining text after last mention
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <span className={className}>{parts.length > 0 ? parts : text}</span>;
}

export function MessageBubble({ message, instanceName, showAvatar = false }: MessageBubbleProps) {
  const isFromMe = message.is_from_me;
  const content = getOmniMessageContent(message);
  const timestamp = formatOmniTimestamp(message.timestamp);
  const status = mapDeliveryStatus(message.delivery_status);
  const senderName = message.sender_name;
  const reactions = message.reactions;

  // Don't render reaction messages as standalone bubbles
  if (message.message_type === 'reaction') {
    return null;
  }

  return (
    <div className={cn('flex gap-2 mb-1 items-start', isFromMe ? 'justify-end' : 'justify-start')}>
      {/* Avatar for group messages (not from me) */}
      {showAvatar && !isFromMe && (
        <Avatar className="h-8 w-8 flex-shrink-0 mt-1">
          <AvatarFallback className="text-xs bg-primary/20">
            {senderName?.charAt(0)?.toUpperCase() || <User className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          'max-w-[65%] rounded-lg shadow-sm relative',
          isFromMe ? 'bg-primary/20 dark:bg-primary/30' : 'bg-card',
          content.type === 'image' || content.type === 'video' || content.type === 'sticker' ? 'p-1' : 'px-3 py-1.5',
        )}
      >
        {/* Sender name in groups */}
        {showAvatar && !isFromMe && senderName && (
          <p className="text-xs font-medium mb-0.5 text-primary">{senderName}</p>
        )}

        {/* Media content */}
        {content.type === 'image' && (
          <ImageMessage message={message} instanceName={instanceName} caption={content.text} />
        )}

        {content.type === 'video' && (
          <VideoMessage message={message} instanceName={instanceName} caption={content.text} />
        )}

        {(content.type === 'audio' || content.type === 'ptt') && (
          <AudioMessage message={message} instanceName={instanceName} isPtt={content.type === 'ptt'} />
        )}

        {content.type === 'document' && (
          <DocumentMessage message={message} instanceName={instanceName} filename={content.filename} />
        )}

        {content.type === 'sticker' && <StickerMessage message={message} instanceName={instanceName} />}

        {/* Text only message */}
        {content.type === 'text' && content.text && (
          <p className="text-sm whitespace-pre-wrap break-words text-foreground">
            <TextWithMentions text={content.text} />
          </p>
        )}

        {/* Location message */}
        {content.type === 'location' && (
          <div className="text-sm">
            <p className="text-foreground">{content.text}</p>
          </div>
        )}

        {/* Contact message */}
        {content.type === 'contact' && (
          <div className="text-sm">
            <p className="text-foreground">{content.text}</p>
          </div>
        )}

        {/* Unsupported */}
        {content.type === 'unsupported' && <p className="text-sm text-muted-foreground italic">{content.text}</p>}

        {/* Media content (transcript/description) */}
        {message.media_content && message.media_content.content && (
          <MediaContentDisplay mediaContent={message.media_content} messageType={message.message_type} />
        )}

        {/* Reactions display */}
        {reactions && reactions.length > 0 && (
          <div className="flex gap-1 mt-1 flex-wrap">
            {Object.entries(groupReactionsByEmoji(reactions)).map(([emoji, senders]) => (
              <span
                key={emoji}
                className="inline-flex items-center bg-gray-100 dark:bg-gray-700 rounded-full px-2 py-0.5 text-xs cursor-default"
                title={senders.map((s) => s.sender_name || 'Unknown').join(', ')}
              >
                {emoji}
                {senders.length > 1 && <span className="ml-1 text-gray-500">{senders.length}</span>}
              </span>
            ))}
          </div>
        )}

        {/* Timestamp and status */}
        <div
          className={cn(
            'flex items-center gap-1 justify-end mt-0.5',
            (content.type === 'image' || content.type === 'video') &&
              'absolute bottom-2 right-2 bg-black/40 rounded px-1',
          )}
        >
          <span
            className={cn(
              'text-[11px]',
              content.type === 'image' || content.type === 'video' ? 'text-white' : 'text-muted-foreground',
            )}
          >
            {timestamp}
          </span>
          {isFromMe && <StatusIcon status={status} light={content.type === 'image' || content.type === 'video'} />}
        </div>
      </div>
    </div>
  );
}

// Image Message Component
function ImageMessage({
  message,
  instanceName,
  caption,
}: {
  message: OmniMessage;
  instanceName: string;
  caption?: string;
}) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        // Use omni endpoint which serves from local storage or downloads
        const result = await api.omni.getMedia(instanceName, message.id);
        setImageSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load image:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchMedia();
  }, [message.id, instanceName]);

  return (
    <div className="relative">
      {loading ? (
        <div className="flex items-center justify-center h-40 w-60 bg-muted rounded-lg animate-pulse">
          <ImageIcon className="h-8 w-8 text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-40 w-60 bg-muted rounded-lg">
          <ImageIcon className="h-8 w-8 text-muted-foreground" />
        </div>
      ) : (
        <img
          src={imageSrc || ''}
          alt="Image"
          className="rounded-lg max-w-full max-h-80 object-contain cursor-pointer hover:opacity-90 transition-opacity"
          onClick={() => imageSrc && window.open(imageSrc, '_blank')}
        />
      )}
      {caption && (
        <p className="text-sm mt-1 px-2 pb-1 text-foreground whitespace-pre-wrap">
          <TextWithMentions text={caption} />
        </p>
      )}
    </div>
  );
}

// Video Message Component
function VideoMessage({
  message,
  instanceName,
  caption,
}: {
  message: OmniMessage;
  instanceName: string;
  caption?: string;
}) {
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        // Use omni endpoint which serves from local storage or downloads
        const result = await api.omni.getMedia(instanceName, message.id);
        setVideoSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load video:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMedia();
  }, [message.id, instanceName]);

  return (
    <div className="relative">
      {loading ? (
        <div className="relative flex items-center justify-center h-40 w-60 bg-muted rounded-lg">
          <div className="bg-black/50 rounded-full p-3">
            <Play className="h-8 w-8 text-white" />
          </div>
        </div>
      ) : (
        <video
          src={videoSrc || ''}
          controls
          className="rounded-lg max-w-full max-h-80"
        />
      )}
      {caption && (
        <p className="text-sm mt-1 px-2 pb-1 text-foreground whitespace-pre-wrap">
          <TextWithMentions text={caption} />
        </p>
      )}
    </div>
  );
}

// Audio Message Component (WhatsApp style waveform player)
function AudioMessage({
  message,
  instanceName,
  isPtt,
}: {
  message: OmniMessage;
  instanceName: string;
  isPtt: boolean;
}) {
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        // Use omni endpoint which serves from local storage or downloads
        const result = await api.omni.getMedia(instanceName, message.id);
        setAudioSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load audio:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMedia();
  }, [message.id, instanceName]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setProgress((audio.currentTime / audio.duration) * 100);
    };
    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };
    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [audioSrc]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const audioDuration = duration;

  return (
    <div className="flex items-center gap-3 min-w-[200px] py-1">
      {audioSrc && <audio ref={audioRef} src={audioSrc} preload="metadata" />}

      {/* Play/Pause button */}
      <button
        onClick={togglePlay}
        disabled={loading || !audioSrc}
        className={cn(
          'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-colors',
          isPtt ? 'bg-primary' : 'bg-muted-foreground',
          loading && 'opacity-50',
        )}
      >
        {loading ? (
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : isPlaying ? (
          <Pause className="h-5 w-5 text-white" fill="white" />
        ) : (
          <Play className="h-5 w-5 text-white ml-0.5" fill="white" />
        )}
      </button>

      {/* Waveform visualization */}
      <div className="flex-1">
        <div className="relative h-2 bg-muted-foreground/30 rounded-full overflow-hidden">
          <div
            className={cn(
              'absolute left-0 top-0 h-full rounded-full transition-all',
              isPtt ? 'bg-primary' : 'bg-muted-foreground',
            )}
            style={{ width: `${progress}%` }}
          />
          {/* Waveform bars (decorative) */}
          <div className="absolute inset-0 flex items-center justify-around px-1">
            {Array.from({ length: 30 }).map((_, i) => (
              <div
                key={i}
                className={cn(
                  'w-0.5 rounded-full',
                  i < (progress / 100) * 30 ? (isPtt ? 'bg-primary' : 'bg-muted-foreground') : 'bg-muted-foreground/40',
                )}
                style={{ height: `${Math.random() * 100}%`, minHeight: '20%' }}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[11px] text-muted-foreground">{formatTime(audioRef.current?.currentTime || 0)}</span>
          <span className="text-[11px] text-muted-foreground">{formatTime(audioDuration)}</span>
        </div>
      </div>

      {/* Mic icon for PTT */}
      {isPtt && <Mic className="h-4 w-4 text-primary flex-shrink-0" />}
    </div>
  );
}

// Document Message Component
function DocumentMessage({
  message,
  instanceName,
  filename,
}: {
  message: OmniMessage;
  instanceName: string;
  filename?: string;
}) {
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      // Use omni endpoint which serves from local storage or downloads
      const result = await api.omni.getMedia(instanceName, message.id);
      const link = document.createElement('a');
      link.href = `data:${result.mimetype};base64,${result.base64}`;
      link.download = result.fileName || filename || 'document';
      link.click();
    } catch (err) {
      console.error('Failed to download document:', err);
    } finally {
      setLoading(false);
    }
  };

  const fileSize = message.media_size;

  return (
    <div
      className="flex items-center gap-3 p-2 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors"
      onClick={handleDownload}
    >
      <div className="flex-shrink-0 w-10 h-12 bg-muted-foreground rounded flex items-center justify-center">
        <FileText className="h-5 w-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{filename || 'Document'}</p>
        {fileSize && (
          <p className="text-xs text-muted-foreground">
            {(fileSize / 1024).toFixed(1)} KB
          </p>
        )}
      </div>
      {loading ? (
        <div className="w-5 h-5 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin" />
      ) : (
        <Download className="h-5 w-5 text-muted-foreground" />
      )}
    </div>
  );
}

// Sticker Message Component
function StickerMessage({ message, instanceName }: { message: OmniMessage; instanceName: string }) {
  const [stickerSrc, setStickerSrc] = useState<string | null>(null);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        // Use omni endpoint which serves from local storage or downloads
        const result = await api.omni.getMedia(instanceName, message.id);
        setStickerSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load sticker:', err);
      }
    };
    fetchMedia();
  }, [message.id, instanceName]);

  return <img src={stickerSrc || ''} alt="Sticker" className="w-32 h-32 object-contain" />;
}

function StatusIcon({ status, light = false }: { status?: string; light?: boolean }) {
  const colorClass = light ? 'text-white' : 'text-muted-foreground';
  const readClass = 'text-primary';

  switch (status) {
    case 'PENDING':
      return <Clock className={cn('h-3 w-3', colorClass)} />;
    case 'SENT':
      return <Check className={cn('h-3.5 w-3.5', colorClass)} />;
    case 'DELIVERED':
      return <CheckCheck className={cn('h-3.5 w-3.5', colorClass)} />;
    case 'READ':
    case 'PLAYED':
      return <CheckCheck className={cn('h-3.5 w-3.5', readClass)} />;
    default:
      return <Check className={cn('h-3.5 w-3.5', colorClass)} />;
  }
}

// Media Content Display Component (transcript for audio, description for images)
function MediaContentDisplay({
  mediaContent,
  messageType: _messageType,
}: {
  mediaContent: OmniMediaContent;
  messageType: string;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const content = mediaContent.content;
  const isLong = content.length > 150;
  const displayContent = isExpanded || !isLong ? content : content.slice(0, 150) + '...';

  // Icon and label based on content type
  const getLabel = () => {
    switch (mediaContent.content_type) {
      case 'audio_transcript':
        return { icon: '🎤', label: 'Transcript' };
      case 'image_description':
        return { icon: '🖼️', label: 'Description' };
      case 'video_description':
        return { icon: '🎬', label: 'Description' };
      case 'document_content':
        return { icon: '📄', label: 'Content' };
      default:
        return { icon: '📝', label: 'Content' };
    }
  };

  const { icon, label } = getLabel();

  return (
    <div className="mt-2 pt-2 border-t border-muted-foreground/20">
      <div className="flex items-center gap-1 mb-1">
        <span className="text-xs">{icon}</span>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">{label}</span>
        {mediaContent.processor_name && (
          <span className="text-[9px] text-muted-foreground/60 ml-auto">
            via {mediaContent.processor_name}
          </span>
        )}
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
        {displayContent}
      </p>
      {isLong && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-[10px] text-primary hover:underline mt-1"
        >
          {isExpanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}

interface MessageContent {
  type:
    | 'text'
    | 'image'
    | 'video'
    | 'audio'
    | 'ptt'
    | 'document'
    | 'sticker'
    | 'location'
    | 'contact'
    | 'reaction'
    | 'unsupported';
  text?: string;
  url?: string;
  filename?: string;
}

// Map OmniMessage delivery_status to StatusIcon format
function mapDeliveryStatus(deliveryStatus: string): string {
  switch (deliveryStatus) {
    case 'pending':
      return 'PENDING';
    case 'sent':
      return 'SENT';
    case 'delivered':
      return 'DELIVERED';
    case 'read':
      return 'READ';
    case 'failed':
      return 'FAILED';
    default:
      return 'SENT';
  }
}

// Format ISO timestamp for display
function formatOmniTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

// Extract content from OmniMessage
function getOmniMessageContent(message: OmniMessage): MessageContent {
  const messageType = message.message_type;
  // Use text_display (with resolved mentions) if available, otherwise fall back to raw text
  const text = message.text_display || message.text || message.caption;
  const caption = message.text_display || message.caption;

  switch (messageType) {
    case 'text':
      return { type: 'text', text };
    case 'image':
      return { type: 'image', text: caption, url: message.media_url ?? undefined };
    case 'video':
      return { type: 'video', text: caption, url: message.media_url ?? undefined };
    case 'audio': {
      // Check channel_data for ptt (push-to-talk/voice note) flag
      const isPtt = message.channel_data?.ptt === true;
      return { type: isPtt ? 'ptt' : 'audio', url: message.media_url ?? undefined };
    }
    case 'document':
      return {
        type: 'document',
        filename: (message.channel_data?.fileName as string) || 'Document',
        url: message.media_url ?? undefined,
      };
    case 'sticker':
      return { type: 'sticker', url: message.media_url ?? undefined };
    case 'location':
      return { type: 'location', text: text || '📍 Location shared' };
    case 'contact':
      return { type: 'contact', text: text || '👤 Contact shared' };
    case 'reaction':
      return { type: 'reaction', text };
    case 'system':
      return { type: 'unsupported', text: '' };
    default:
      return { type: 'text', text: text || `[${messageType || 'Unknown'}]` };
  }
}

// Legacy: Extract content from EvolutionMessage (kept for reference)
function _getMessageContent(message: EvolutionMessage): MessageContent {
  const msg = message.message || {};
  const messageType = message.messageType;

  // Handle by messageType first (more reliable)
  if (messageType === 'conversation' || msg.conversation) {
    return { type: 'text', text: msg.conversation };
  }
  if (messageType === 'extendedTextMessage' || msg.extendedTextMessage?.text) {
    return { type: 'text', text: msg.extendedTextMessage?.text };
  }
  if (messageType === 'imageMessage' || msg.imageMessage) {
    return {
      type: 'image',
      text: msg.imageMessage?.caption,
      url: msg.imageMessage?.url,
    };
  }
  if (messageType === 'videoMessage' || msg.videoMessage) {
    return {
      type: 'video',
      text: msg.videoMessage?.caption,
      url: msg.videoMessage?.url,
    };
  }
  if (messageType === 'audioMessage' || msg.audioMessage) {
    const isPtt = msg.audioMessage?.ptt === true;
    return {
      type: isPtt ? 'ptt' : 'audio',
      url: msg.audioMessage?.url,
    };
  }
  if (messageType === 'documentMessage' || msg.documentMessage) {
    return {
      type: 'document',
      filename: msg.documentMessage?.fileName,
      url: msg.documentMessage?.url,
    };
  }
  if (messageType === 'stickerMessage' || msg.stickerMessage) {
    return {
      type: 'sticker',
      url: msg.stickerMessage?.url,
    };
  }
  if (messageType === 'locationMessage' || msg.locationMessage) {
    return {
      type: 'location',
      text: `📍 Location: ${msg.locationMessage?.degreesLatitude?.toFixed(4)}, ${msg.locationMessage?.degreesLongitude?.toFixed(4)}`,
    };
  }
  if (messageType === 'contactMessage' || msg.contactMessage) {
    return {
      type: 'contact',
      text: `👤 ${msg.contactMessage?.displayName}`,
    };
  }
  if (messageType === 'reactionMessage' || msg.reactionMessage) {
    return {
      type: 'reaction',
      text: msg.reactionMessage?.text || '❤️',
    };
  }

  // Skip system messages
  if (messageType === 'protocolMessage' || messageType === 'senderKeyDistributionMessage') {
    return { type: 'unsupported', text: '' };
  }

  return { type: 'unsupported', text: `[${messageType || 'Unknown message type'}]` };
}

function _formatMessageTime(timestamp: number | undefined): string {
  return formatTimeFromTimestamp(timestamp);
}
