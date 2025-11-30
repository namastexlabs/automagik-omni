import { useState, useRef, useCallback, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, Paperclip, Smile, Loader2, Mic, X, Image, FileText, Play, Pause, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { useDropzone } from 'react-dropzone';
import Picker from '@emoji-mart/react';
import data from '@emoji-mart/data';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn, api } from '@/lib';

interface ChatInputProps {
  instanceName: string;
  remoteJid: string;
  onMessageSent?: () => void;
}

export function ChatInput({ instanceName, remoteJid, onMessageSent }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [isPlayingPreview, setIsPlayingPreview] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // Send text message mutation
  const sendTextMutation = useMutation({
    mutationFn: (text: string) => {
      const number = remoteJid.split('@')[0];
      return api.evolution.sendText(instanceName, { number, text });
    },
    onSuccess: () => {
      setMessage('');
      onMessageSent?.();
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    },
    onError: (error: Error) => {
      toast.error(`Failed to send: ${error.message}`);
    },
  });

  // Send media mutation
  const sendMediaMutation = useMutation({
    mutationFn: async (file: File) => {
      const number = remoteJid.split('@')[0];
      const base64 = await fileToBase64(file);
      const mediaType = file.type.startsWith('image/') ? 'image' :
                       file.type.startsWith('video/') ? 'video' :
                       file.type.startsWith('audio/') ? 'audio' : 'document';

      return api.evolution.sendMedia(instanceName, {
        number,
        mediatype: mediaType,
        media: base64,
        fileName: file.name,
        mimetype: file.type,
      });
    },
    onSuccess: () => {
      onMessageSent?.();
      toast.success('Media sent');
    },
    onError: (error: Error) => {
      toast.error(`Failed to send media: ${error.message}`);
    },
  });

  // Send audio mutation
  const sendAudioMutation = useMutation({
    mutationFn: async (blob: Blob) => {
      const number = remoteJid.split('@')[0];
      const base64 = await blobToBase64(blob);
      return api.evolution.sendWhatsAppAudio(instanceName, {
        number,
        audio: base64,
        encoding: true,
      });
    },
    onSuccess: () => {
      setAudioBlob(null);
      setRecordingTime(0);
      onMessageSent?.();
      toast.success('Audio sent');
    },
    onError: (error: Error) => {
      toast.error(`Failed to send audio: ${error.message}`);
    },
  });

  const handleSend = useCallback(() => {
    const text = message.trim();
    if (!text || sendTextMutation.isPending) return;
    sendTextMutation.mutate(text);
  }, [message, sendTextMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
  };

  const handleEmojiSelect = (emoji: any) => {
    setMessage(prev => prev + emoji.native);
    textareaRef.current?.focus();
  };

  // File drop handler
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      sendMediaMutation.mutate(acceptedFiles[0]);
    }
    setShowAttachMenu(false);
  }, [sendMediaMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    noClick: true,
    noKeyboard: true,
  });

  const handleFileSelect = (type: 'image' | 'document') => {
    if (fileInputRef.current) {
      fileInputRef.current.accept = type === 'image' ? 'image/*,video/*' : '*';
      fileInputRef.current.click();
    }
    setShowAttachMenu(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      sendMediaMutation.mutate(file);
    }
    e.target.value = '';
  };

  // Voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100);
      setIsRecording(true);
      setRecordingTime(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1);
      }, 1000);

    } catch (error) {
      toast.error('Could not access microphone');
      console.error('Recording error:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
    }
    setIsRecording(false);
  };

  const cancelRecording = () => {
    stopRecording();
    setAudioBlob(null);
    setRecordingTime(0);
    audioChunksRef.current = [];
  };

  const sendRecording = () => {
    if (audioBlob) {
      sendAudioMutation.mutate(audioBlob);
    }
  };

  const togglePreviewPlayback = () => {
    if (!audioBlob) return;

    if (!audioPreviewRef.current) {
      audioPreviewRef.current = new Audio(URL.createObjectURL(audioBlob));
      audioPreviewRef.current.onended = () => setIsPlayingPreview(false);
    }

    if (isPlayingPreview) {
      audioPreviewRef.current.pause();
      setIsPlayingPreview(false);
    } else {
      audioPreviewRef.current.play();
      setIsPlayingPreview(true);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isPending = sendTextMutation.isPending || sendMediaMutation.isPending || sendAudioMutation.isPending;

  // Recording UI
  if (isRecording || audioBlob) {
    return (
      <div className="bg-muted/50 border-t border-border px-4 py-3">
        <div className="flex items-center gap-3">
          {/* Cancel button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-10 w-10 text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
            onClick={cancelRecording}
          >
            <Trash2 className="h-5 w-5" />
          </Button>

          {/* Recording indicator / Preview */}
          <div className="flex-1 flex items-center gap-3 bg-background rounded-full px-4 py-2">
            {isRecording ? (
              <>
                <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
                <span className="text-sm font-medium text-foreground">
                  Recording...
                </span>
              </>
            ) : (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={togglePreviewPlayback}
              >
                {isPlayingPreview ? (
                  <Pause className="h-4 w-4" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
            )}

            {/* Waveform placeholder */}
            <div className="flex-1 flex items-center gap-0.5 h-6">
              {Array.from({ length: 30 }).map((_, i) => (
                <div
                  key={i}
                  className={cn(
                    "w-1 rounded-full transition-all",
                    isRecording
                      ? "bg-primary animate-pulse"
                      : "bg-muted-foreground"
                  )}
                  style={{
                    height: `${Math.random() * 16 + 8}px`,
                    animationDelay: `${i * 50}ms`,
                  }}
                />
              ))}
            </div>

            <span className="text-sm text-muted-foreground min-w-[40px]">
              {formatTime(recordingTime)}
            </span>
          </div>

          {/* Stop/Send button */}
          {isRecording ? (
            <Button
              size="icon"
              className="h-10 w-10 bg-destructive hover:bg-destructive/90"
              onClick={stopRecording}
            >
              <div className="h-4 w-4 rounded-sm bg-white" />
            </Button>
          ) : (
            <Button
              size="icon"
              className="h-10 w-10"
              onClick={sendRecording}
              disabled={sendAudioMutation.isPending}
            >
              {sendAudioMutation.isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </Button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={cn(
        "bg-muted/50 border-t border-border px-4 py-3",
        isDragActive && "ring-2 ring-primary ring-inset"
      )}
    >
      <input {...getInputProps()} />
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
      />

      {isDragActive && (
        <div className="absolute inset-0 bg-primary/10 flex items-center justify-center z-10 pointer-events-none">
          <div className="bg-card rounded-lg p-4 shadow-lg">
            <p className="text-primary font-medium">Drop file to send</p>
          </div>
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Emoji picker */}
        <Popover open={showEmojiPicker} onOpenChange={setShowEmojiPicker}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="flex-shrink-0 h-10 w-10 text-muted-foreground hover:text-primary"
            >
              <Smile className="h-6 w-6" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            className="w-auto p-0 border-0"
            side="top"
            align="start"
            sideOffset={8}
          >
            <Picker
              data={data}
              onEmojiSelect={handleEmojiSelect}
              theme="light"
              previewPosition="none"
              skinTonePosition="search"
              maxFrequentRows={2}
            />
          </PopoverContent>
        </Popover>

        {/* Attachment menu */}
        <Popover open={showAttachMenu} onOpenChange={setShowAttachMenu}>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "flex-shrink-0 h-10 w-10 text-muted-foreground hover:text-primary transition-transform",
                showAttachMenu && "rotate-45"
              )}
            >
              <Paperclip className="h-6 w-6" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            className="w-auto p-2"
            side="top"
            align="start"
            sideOffset={8}
          >
            <div className="flex flex-col gap-1">
              <Button
                variant="ghost"
                className="justify-start gap-3 h-12 px-4"
                onClick={() => handleFileSelect('image')}
              >
                <div className="h-10 w-10 rounded-full bg-purple-500 flex items-center justify-center">
                  <Image className="h-5 w-5 text-white" />
                </div>
                <span>Photos & Videos</span>
              </Button>
              <Button
                variant="ghost"
                className="justify-start gap-3 h-12 px-4"
                onClick={() => handleFileSelect('document')}
              >
                <div className="h-10 w-10 rounded-full bg-blue-500 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-white" />
                </div>
                <span>Document</span>
              </Button>
            </div>
          </PopoverContent>
        </Popover>

        {/* Message input */}
        <div className="flex-1 bg-background rounded-lg">
          <Textarea
            ref={textareaRef}
            placeholder="Type a message"
            value={message}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            className="min-h-10 max-h-36 resize-none py-2.5 px-3 border-0 bg-transparent focus-visible:ring-0"
            rows={1}
          />
        </div>

        {/* Send or Mic button */}
        {message.trim() ? (
          <Button
            size="icon"
            className="flex-shrink-0 h-10 w-10"
            onClick={handleSend}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  size="icon"
                  variant="ghost"
                  className="flex-shrink-0 h-10 w-10 text-muted-foreground hover:text-primary"
                  onClick={startRecording}
                  disabled={isPending}
                >
                  <Mic className="h-6 w-6" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Record voice message</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
    </div>
  );
}

// Utility functions
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Remove data URL prefix if present
      const base64 = result.includes(',') ? result.split(',')[1] : result;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.includes(',') ? result.split(',')[1] : result;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
