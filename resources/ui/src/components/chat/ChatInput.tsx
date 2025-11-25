import { useState, useRef, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, Paperclip, Smile, Loader2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { api } from '@/lib/api';

interface ChatInputProps {
  instanceName: string;
  remoteJid: string;
  onMessageSent?: () => void;
}

export function ChatInput({ instanceName, remoteJid, onMessageSent }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const sendMutation = useMutation({
    mutationFn: (text: string) => {
      // Extract phone number from JID
      const number = remoteJid.split('@')[0];
      return api.evolution.sendText(instanceName, { number, text });
    },
    onSuccess: () => {
      setMessage('');
      onMessageSent?.();
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    },
    onError: (error: Error) => {
      toast.error(`Failed to send: ${error.message}`);
    },
  });

  const handleSend = useCallback(() => {
    const text = message.trim();
    if (!text || sendMutation.isPending) return;
    sendMutation.mutate(text);
  }, [message, sendMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
  };

  return (
    <div className="border-t p-3">
      <div className="flex items-end gap-2">
        {/* Emoji button (placeholder for future) */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="flex-shrink-0 h-10 w-10" disabled>
                <Smile className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Emoji (coming soon)</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Attachment button (placeholder for future) */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="flex-shrink-0 h-10 w-10" disabled>
                <Paperclip className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Attach file (coming soon)</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Message input */}
        <Textarea
          ref={textareaRef}
          placeholder="Type a message..."
          value={message}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          className="min-h-10 max-h-36 resize-none py-2.5"
          rows={1}
        />

        {/* AI button (placeholder for future Genie integration) */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" className="flex-shrink-0 h-10 w-10" disabled>
                <Sparkles className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>AI assist (coming soon)</TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* Send button */}
        <Button
          size="icon"
          className="flex-shrink-0 h-10 w-10"
          onClick={handleSend}
          disabled={!message.trim() || sendMutation.isPending}
        >
          {sendMutation.isPending ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Send className="h-5 w-5" />
          )}
        </Button>
      </div>
    </div>
  );
}
