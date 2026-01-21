import { useRef, useEffect, useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { Loader2, User, Users, MoreVertical } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { api } from '@/lib';
import type { EvolutionChat, EvolutionMessage } from '@/lib';

interface ChatViewProps {
  instanceName: string;
  chat: EvolutionChat;
}

export function ChatView({ instanceName, chat }: ChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const remoteJid = chat.remoteJid || chat.id || '';
  const name = chat.name || chat.pushName || (remoteJid ? remoteJid.split('@')[0] : 'Unknown');
  const isGroup = remoteJid?.includes('@g.us') || chat.isGroup;

  // For LID chats, we need to fetch messages by both LID and resolved phone JID
  // because sent messages are stored with the phone JID, not the LID
  const phoneJid = chat.resolvedPhoneNumber ? `${chat.resolvedPhoneNumber}@s.whatsapp.net` : null;
  const jidsToQuery = phoneJid && phoneJid !== remoteJid ? [remoteJid, phoneJid] : [remoteJid];

  // Fetch messages for all relevant JIDs
  const messageQueries = useQueries({
    queries: jidsToQuery.map((jid) => ({
      queryKey: ['messages', instanceName, jid],
      queryFn: () =>
        api.evolution.findMessages(instanceName, {
          where: { key: { remoteJid: jid } },
          limit: 100,
        }),
      refetchInterval: 5000,
    })),
  });

  const isLoading = messageQueries.some((q) => q.isLoading);
  const refetch = () => messageQueries.forEach((q) => q.refetch());

  // Merge messages from all queries and deduplicate by message ID
  const messages: EvolutionMessage[] = useMemo(() => {
    const allMessages: EvolutionMessage[] = [];
    const seenIds = new Set<string>();

    for (const query of messageQueries) {
      const data = query.data;
      const msgs: EvolutionMessage[] = Array.isArray(data) ? data : [];
      for (const msg of msgs) {
        const id = msg.key?.id;
        if (id && !seenIds.has(id)) {
          seenIds.add(id);
          allMessages.push(msg);
        } else if (!id) {
          allMessages.push(msg);
        }
      }
    }

    return allMessages;
  }, [messageQueries]);

  // Sort messages by timestamp
  const sortedMessages = [...messages].sort(
    (a, b) => (Number(a.messageTimestamp) || 0) - (Number(b.messageTimestamp) || 0),
  );

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

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
          <h2 className="font-medium truncate text-foreground">{name}</h2>
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
        <Button variant="ghost" size="icon" className="text-muted-foreground">
          <MoreVertical className="h-5 w-5" />
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
                  key={message.key?.id || index}
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
