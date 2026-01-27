import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, MessageSquare, AlertCircle } from 'lucide-react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ChatList } from './ChatList';
import { ChatView } from './ChatView';
import { api } from '@/lib';
import type { EvolutionChat, OmniChatsResponse } from '@/lib';

interface ChatLayoutProps {
  instanceName: string;
}

// Transform OmniChat to EvolutionChat format for compatibility with ChatList/ChatListItem
function transformOmniChatToEvolution(chat: OmniChatsResponse['chats'][0]): EvolutionChat {
  const channelData = chat.channel_data as {
    last_message_preview?: string;
    message_count?: number;
    contact_phone?: string;
  } | undefined;

  return {
    id: chat.id,
    remoteJid: chat.id, // id is the JID in our schema
    name: chat.name || 'Unknown',
    pushName: chat.name,
    profilePicUrl: chat.avatar_url || undefined,
    unreadCount: chat.unread_count || 0,
    isGroup: chat.chat_type === 'group',
    // Create a lastMessage structure for preview and timestamp
    lastMessage: channelData?.last_message_preview ? {
      messageTimestamp: chat.last_message_at ? Math.floor(new Date(chat.last_message_at).getTime() / 1000) : undefined,
      message: { conversation: channelData.last_message_preview },
    } : undefined,
    updatedAt: chat.last_message_at || undefined,
  } as EvolutionChat;
}

export function ChatLayout({ instanceName }: ChatLayoutProps) {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);

  // Fetch chats from our local omni_chats table (fast, pre-sorted by last_message_at)
  const {
    data: chatsResponse,
    isLoading,
    isError,
    error: chatsErrorData,
  } = useQuery<OmniChatsResponse>({
    queryKey: ['chats', instanceName],
    queryFn: () => api.chats.list(instanceName, { page_size: 500 }),
    refetchInterval: 30000,
  });

  // Transform OmniChat[] to EvolutionChat[] for compatibility with existing components
  const chats = useMemo(() => {
    if (!chatsResponse?.chats) return [];
    return chatsResponse.chats.map(transformOmniChatToEvolution);
  }, [chatsResponse]);

  const selectedChat = chats.find((c) => c.id === selectedChatId || c.remoteJid === selectedChatId);

  // Handle errors loading chats
  if (isError && !isLoading) {
    const errorMessage = chatsErrorData instanceof Error ? chatsErrorData.message : 'Failed to load chats';
    return (
      <div className="flex items-center justify-center h-full bg-background">
        <div className="max-w-md text-center space-y-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error Loading Chats</AlertTitle>
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <ResizablePanelGroup direction="horizontal" className="h-full">
      {/* Chat List */}
      <ResizablePanel defaultSize={35} minSize={25} maxSize={50}>
        <ChatList
          instanceName={instanceName}
          chats={chats}
          selectedChatId={selectedChatId}
          onSelectChat={setSelectedChatId}
        />
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* Chat View */}
      <ResizablePanel defaultSize={65}>
        {selectedChat ? (
          <ChatView instanceName={instanceName} chat={selectedChat} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full bg-muted/20 text-muted-foreground">
            <div className="text-center">
              <MessageSquare className="h-16 w-16 mx-auto mb-4 opacity-30" />
              <h2 className="text-2xl font-light mb-2 text-foreground">Omni Hub</h2>
              <p className="text-sm">Select a chat to start messaging</p>
            </div>
          </div>
        )}
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
