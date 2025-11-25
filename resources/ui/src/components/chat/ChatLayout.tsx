import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, MessageSquare } from 'lucide-react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import { ChatList } from './ChatList';
import { ChatView } from './ChatView';
import { api } from '@/lib/api';

interface ChatLayoutProps {
  instanceName: string;
}

export function ChatLayout({ instanceName }: ChatLayoutProps) {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);

  // Fetch chats
  const { data: chatsResponse, isLoading } = useQuery({
    queryKey: ['chats', instanceName],
    queryFn: () => api.evolution.findChats(instanceName),
    refetchInterval: 30000,
  });

  const chats = Array.isArray(chatsResponse) ? chatsResponse : [];
  const selectedChat = chats.find((c: any) => c.id === selectedChatId || c.remoteJid === selectedChatId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
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
          <ChatView
            instanceName={instanceName}
            chat={selectedChat}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <MessageSquare className="h-16 w-16 mb-4 opacity-20" />
            <p className="text-lg">Select a chat to start messaging</p>
            <p className="text-sm mt-1">Choose from your conversations on the left</p>
          </div>
        )}
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
