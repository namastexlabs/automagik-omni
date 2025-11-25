import { useState, useEffect, useRef } from 'react';
import { Check, CheckCheck, Clock, User, Play, Pause, Mic, Download, FileText, Image as ImageIcon } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api';

interface MessageBubbleProps {
  message: any;
  instanceName: string;
  showAvatar?: boolean;
}

export function MessageBubble({ message, instanceName, showAvatar = false }: MessageBubbleProps) {
  const isFromMe = message.key?.fromMe;
  const content = getMessageContent(message);
  const timestamp = formatMessageTime(message.messageTimestamp);
  const status = message.status;
  const senderName = message.pushName;

  return (
    <div
      className={cn(
        'flex gap-2 mb-1',
        isFromMe ? 'justify-end' : 'justify-start'
      )}
    >
      {/* Avatar for group messages (not from me) */}
      {showAvatar && !isFromMe && (
        <Avatar className="h-8 w-8 flex-shrink-0 mt-auto">
          <AvatarFallback className="text-xs bg-primary/20">
            {senderName?.charAt(0)?.toUpperCase() || <User className="h-4 w-4" />}
          </AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          'max-w-[65%] rounded-lg shadow-sm relative',
          isFromMe
            ? 'bg-primary/20 dark:bg-primary/30'
            : 'bg-card',
          content.type === 'image' || content.type === 'video' || content.type === 'sticker'
            ? 'p-1'
            : 'px-3 py-1.5'
        )}
      >
        {/* Sender name in groups */}
        {showAvatar && !isFromMe && senderName && (
          <p className="text-xs font-medium mb-0.5 text-primary">
            {senderName}
          </p>
        )}

        {/* Media content */}
        {content.type === 'image' && (
          <ImageMessage
            message={message}
            instanceName={instanceName}
            caption={content.text}
          />
        )}

        {content.type === 'video' && (
          <VideoMessage
            message={message}
            instanceName={instanceName}
            caption={content.text}
          />
        )}

        {(content.type === 'audio' || content.type === 'ptt') && (
          <AudioMessage
            message={message}
            instanceName={instanceName}
            isPtt={content.type === 'ptt'}
          />
        )}

        {content.type === 'document' && (
          <DocumentMessage
            message={message}
            instanceName={instanceName}
            filename={content.filename}
          />
        )}

        {content.type === 'sticker' && (
          <StickerMessage
            message={message}
            instanceName={instanceName}
          />
        )}

        {/* Text only message */}
        {content.type === 'text' && content.text && (
          <p className="text-sm whitespace-pre-wrap break-words text-foreground">
            {content.text}
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

        {/* Reaction message */}
        {content.type === 'reaction' && (
          <div className="text-2xl">{content.text}</div>
        )}

        {/* Unsupported */}
        {content.type === 'unsupported' && (
          <p className="text-sm text-muted-foreground italic">{content.text}</p>
        )}

        {/* Timestamp and status */}
        <div
          className={cn(
            'flex items-center gap-1 justify-end mt-0.5',
            (content.type === 'image' || content.type === 'video') && 'absolute bottom-2 right-2 bg-black/40 rounded px-1'
          )}
        >
          <span className={cn(
            'text-[11px]',
            (content.type === 'image' || content.type === 'video')
              ? 'text-white'
              : 'text-muted-foreground'
          )}>
            {timestamp}
          </span>
          {isFromMe && <StatusIcon status={status} light={content.type === 'image' || content.type === 'video'} />}
        </div>
      </div>
    </div>
  );
}

// Image Message Component
function ImageMessage({ message, instanceName, caption }: { message: any; instanceName: string; caption?: string }) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const thumbnail = message.message?.imageMessage?.jpegThumbnail;

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        const result = await api.evolution.getBase64FromMediaMessage(instanceName, {
          message: { key: { id: message.key.id, remoteJid: message.key.remoteJid } },
        });
        setImageSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load image:', err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchMedia();
  }, [message.key.id, message.key.remoteJid, instanceName]);

  const thumbnailSrc = thumbnail ? `data:image/jpeg;base64,${thumbnail}` : null;

  return (
    <div className="relative">
      {loading && thumbnailSrc ? (
        <img
          src={thumbnailSrc}
          alt="Loading..."
          className="rounded-lg max-w-full max-h-80 object-contain blur-sm"
        />
      ) : error ? (
        <div className="flex items-center justify-center h-40 w-60 bg-muted rounded-lg">
          <ImageIcon className="h-8 w-8 text-muted-foreground" />
        </div>
      ) : (
        <img
          src={imageSrc || thumbnailSrc || ''}
          alt="Image"
          className="rounded-lg max-w-full max-h-80 object-contain cursor-pointer hover:opacity-90 transition-opacity"
          onClick={() => imageSrc && window.open(imageSrc, '_blank')}
        />
      )}
      {caption && (
        <p className="text-sm mt-1 px-2 pb-1 text-foreground whitespace-pre-wrap">
          {caption}
        </p>
      )}
    </div>
  );
}

// Video Message Component
function VideoMessage({ message, instanceName, caption }: { message: any; instanceName: string; caption?: string }) {
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const thumbnail = message.message?.videoMessage?.jpegThumbnail;

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        const result = await api.evolution.getBase64FromMediaMessage(instanceName, {
          message: { key: { id: message.key.id, remoteJid: message.key.remoteJid } },
          convertToMp4: true,
        });
        setVideoSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load video:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMedia();
  }, [message.key.id, message.key.remoteJid, instanceName]);

  const thumbnailSrc = thumbnail ? `data:image/jpeg;base64,${thumbnail}` : null;

  return (
    <div className="relative">
      {loading ? (
        <div className="relative">
          {thumbnailSrc && (
            <img src={thumbnailSrc} alt="Video thumbnail" className="rounded-lg max-w-full max-h-80 blur-sm" />
          )}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-black/50 rounded-full p-3">
              <Play className="h-8 w-8 text-white" />
            </div>
          </div>
        </div>
      ) : (
        <video
          src={videoSrc || ''}
          controls
          className="rounded-lg max-w-full max-h-80"
          poster={thumbnailSrc || undefined}
        />
      )}
      {caption && (
        <p className="text-sm mt-1 px-2 pb-1 text-foreground whitespace-pre-wrap">
          {caption}
        </p>
      )}
    </div>
  );
}

// Audio Message Component (WhatsApp style waveform player)
function AudioMessage({ message, instanceName, isPtt }: { message: any; instanceName: string; isPtt: boolean }) {
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        const result = await api.evolution.getBase64FromMediaMessage(instanceName, {
          message: { key: { id: message.key.id, remoteJid: message.key.remoteJid } },
        });
        setAudioSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load audio:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchMedia();
  }, [message.key.id, message.key.remoteJid, instanceName]);

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

  const audioDuration = message.message?.audioMessage?.seconds || duration;

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
          loading && 'opacity-50'
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
              isPtt ? 'bg-primary' : 'bg-muted-foreground'
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
                  i < (progress / 100) * 30 ? (isPtt ? 'bg-primary' : 'bg-muted-foreground') : 'bg-muted-foreground/40'
                )}
                style={{ height: `${Math.random() * 100}%`, minHeight: '20%' }}
              />
            ))}
          </div>
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[11px] text-muted-foreground">
            {formatTime(audioRef.current?.currentTime || 0)}
          </span>
          <span className="text-[11px] text-muted-foreground">
            {formatTime(audioDuration)}
          </span>
        </div>
      </div>

      {/* Mic icon for PTT */}
      {isPtt && (
        <Mic className="h-4 w-4 text-primary flex-shrink-0" />
      )}
    </div>
  );
}

// Document Message Component
function DocumentMessage({ message, instanceName, filename }: { message: any; instanceName: string; filename?: string }) {
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      const result = await api.evolution.getBase64FromMediaMessage(instanceName, {
        message: { key: { id: message.key.id, remoteJid: message.key.remoteJid } },
      });
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

  const docMessage = message.message?.documentMessage;
  const pageCount = docMessage?.pageCount;
  const fileSize = docMessage?.fileLength?.low;

  return (
    <div
      className="flex items-center gap-3 p-2 bg-muted rounded-lg cursor-pointer hover:bg-muted/80 transition-colors"
      onClick={handleDownload}
    >
      <div className="flex-shrink-0 w-10 h-12 bg-muted-foreground rounded flex items-center justify-center">
        <FileText className="h-5 w-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {filename || 'Document'}
        </p>
        <p className="text-xs text-muted-foreground">
          {pageCount && `${pageCount} pages • `}
          {fileSize && `${(fileSize / 1024).toFixed(1)} KB`}
        </p>
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
function StickerMessage({ message, instanceName }: { message: any; instanceName: string }) {
  const [stickerSrc, setStickerSrc] = useState<string | null>(null);

  useEffect(() => {
    const fetchMedia = async () => {
      try {
        const result = await api.evolution.getBase64FromMediaMessage(instanceName, {
          message: { key: { id: message.key.id, remoteJid: message.key.remoteJid } },
        });
        setStickerSrc(`data:${result.mimetype};base64,${result.base64}`);
      } catch (err) {
        console.error('Failed to load sticker:', err);
      }
    };
    fetchMedia();
  }, [message.key.id, message.key.remoteJid, instanceName]);

  return (
    <img
      src={stickerSrc || ''}
      alt="Sticker"
      className="w-32 h-32 object-contain"
    />
  );
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

interface MessageContent {
  type: 'text' | 'image' | 'video' | 'audio' | 'ptt' | 'document' | 'sticker' | 'location' | 'contact' | 'reaction' | 'unsupported';
  text?: string;
  url?: string;
  filename?: string;
}

function getMessageContent(message: any): MessageContent {
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

function formatMessageTime(timestamp: number | undefined): string {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
