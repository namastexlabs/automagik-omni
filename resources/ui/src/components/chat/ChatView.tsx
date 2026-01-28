import { useRef, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, User, Users, Pause, Play } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { api } from '@/lib';
import type { EvolutionChat } from '@/lib';

interface ChatViewProps {
  instanceName: string;
  chat: EvolutionChat;
}

export function ChatView({ instanceName, chat }: ChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const remoteJid = chat.remoteJid || chat.id || '';
  const name = chat.name || chat.pushName || (remoteJid ? remoteJid.split('@')[0] : 'Unknown');
  const isGroup = remoteJid?.includes('@g.us') || chat.isGroup;

  // Agent pause state
  const [isAgentPaused, setIsAgentPaused] = useState(false);
  const [blockRuleId, setBlockRuleId] = useState<number | null>(null);
  const [isToggling, setIsToggling] = useState(false);

  // For block rules: extract phone/digits and add + prefix (matches backend logic)
  // Backend does: remoteJid.split("@")[0] → keep digits only → add "+"
  const extractBlockIdentifier = (): string | null => {
    // For regular chats, prefer resolved phone number (handles LID chats)
    if (!isGroup && chat.resolvedPhoneNumber) {
      return `+${chat.resolvedPhoneNumber}`;
    }
    // Extract from JID: strip domain, keep digits only
    if (remoteJid) {
      const raw = remoteJid.split('@')[0];
      const digitsOnly = raw.replace(/\D/g, '');
      if (digitsOnly) {
        return `+${digitsOnly}`;
      }
    }
    return null;
  };
  const blockIdentifier = extractBlockIdentifier();

  // Query existing block rules to check if this chat is paused
  const { refetch: refetchRules } = useQuery({
    queryKey: ['accessRules', instanceName, blockIdentifier],
    queryFn: () => api.accessRules.list({ instance_name: instanceName, rule_type: 'block' }),
    enabled: !!blockIdentifier,
    onSuccess: (rules) => {
      const existingRule = rules.find((r) => r.phone_number === blockIdentifier);
      setIsAgentPaused(!!existingRule);
      setBlockRuleId(existingRule?.id ?? null);
    },
  });

  // Toggle agent pause
  const handleTogglePause = async () => {
    if (!blockIdentifier || isToggling) return;

    setIsToggling(true);
    try {
      if (isAgentPaused && blockRuleId) {
        // Resume: delete the block rule
        await api.accessRules.delete(blockRuleId);
        setIsAgentPaused(false);
        setBlockRuleId(null);
      } else {
        // Pause: create a block rule
        const rule = await api.accessRules.create({
          phone_number: blockIdentifier,
          rule_type: 'block',
          instance_name: instanceName,
        });
        setIsAgentPaused(true);
        setBlockRuleId(rule.id);
      }
      refetchRules();
    } catch (error) {
      console.error('Failed to toggle agent pause:', error);
    } finally {
      setIsToggling(false);
    }
  };

  // Fetch messages from local omni_messages table (unified by canonical_chat_id)
  // This single query handles both @lid and @s.whatsapp.net JID formats
  const { data: messagesData, isLoading, refetch } = useQuery({
    queryKey: ['omni-messages', instanceName, remoteJid],
    queryFn: () => api.omni.getMessages(instanceName, remoteJid, { page_size: 100 }),
    refetchInterval: 5000,
  });

  // Messages come pre-sorted (newest first from API), with reactions pre-attached
  // Reverse to oldest-first for display
  const sortedMessages = [...(messagesData?.messages ?? [])].reverse();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [sortedMessages.length]);

  const handleMessageSent = () => {
    refetch();
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-muted/50 border-b border-border px-4 py-2 flex items-center gap-3">
        <Avatar className="h-10 w-10">
          <AvatarImage src={chat.profilePicUrl || chat.profilePictureUrl} />
          <AvatarFallback className="bg-primary/20 text-primary">
            {isGroup ? <Users className="h-5 w-5" /> : <User className="h-5 w-5" />}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="font-medium truncate text-foreground">{name}</h2>
            {isAgentPaused && (
              <Badge variant="secondary" className="text-xs shrink-0">
                Agent Paused
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground truncate">
            {isGroup
              ? 'Group chat'
              : chat.resolvedPhoneNumber
                ? `+${chat.resolvedPhoneNumber}`
                : remoteJid
                  ? `+${remoteJid.split('@')[0]}`
                  : 'Unknown'}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className={isAgentPaused ? 'text-orange-500 hover:text-orange-600' : 'text-muted-foreground'}
          onClick={handleTogglePause}
          disabled={isToggling || !blockIdentifier}
          title={isAgentPaused ? 'Resume Agent' : 'Pause Agent'}
        >
          {isToggling ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : isAgentPaused ? (
            <Play className="h-5 w-5" />
          ) : (
            <Pause className="h-5 w-5" />
          )}
        </Button>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 bg-muted/20" ref={scrollRef}>
        <div className="p-3">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : sortedMessages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">No messages yet</div>
          ) : (
            <div className="space-y-1">
              {sortedMessages.map((message, index) => (
                <MessageBubble
                  key={message.id || index}
                  message={message}
                  instanceName={instanceName}
                  showAvatar={isGroup}
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <ChatInput
        instanceName={instanceName}
        remoteJid={remoteJid}
        resolvedPhoneNumber={chat.resolvedPhoneNumber}
        onMessageSent={handleMessageSent}
      />
    </div>
  );
}
