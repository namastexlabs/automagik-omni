import { useState, useMemo } from 'react';
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

// Format phone number or LID to display name
function formatDisplayName(jid: string | undefined): string {
  if (!jid) return 'Unknown';
  const id = jid.split('@')[0];

  // If it's a LID (Linked ID), just show it as-is or truncate
  if (jid.includes('@lid')) {
    return id.length > 12 ? `${id.slice(0, 12)}...` : id;
  }

  // Format phone number with country code
  if (id.length >= 10) {
    // Try to format as phone number
    const cleaned = id.replace(/\D/g, '');
    if (cleaned.length === 13) {
      // Brazilian format: +55 12 98765-4321
      return `+${cleaned.slice(0, 2)} ${cleaned.slice(2, 4)} ${cleaned.slice(4, 9)}-${cleaned.slice(9)}`;
    } else if (cleaned.length >= 10) {
      // Generic format
      return `+${cleaned}`;
    }
  }

  return id;
}

export function ChatLayout({ instanceName }: ChatLayoutProps) {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);

  // Fetch chats
  const { data: chatsResponse, isLoading: chatsLoading } = useQuery({
    queryKey: ['chats', instanceName],
    queryFn: () => api.evolution.findChats(instanceName),
    refetchInterval: 30000,
  });

  // Fetch groups to get proper group names
  const { data: groupsResponse } = useQuery({
    queryKey: ['groups', instanceName],
    queryFn: () => api.evolution.fetchAllGroups(instanceName),
    refetchInterval: 60000,
  });

  // Create a map of group IDs to group info
  const groupsMap = useMemo(() => {
    const map = new Map<string, any>();
    if (Array.isArray(groupsResponse)) {
      groupsResponse.forEach((group: any) => {
        map.set(group.id, group);
      });
    }
    return map;
  }, [groupsResponse]);

  // Merge chats with group info
  const chats = useMemo(() => {
    const rawChats = Array.isArray(chatsResponse) ? chatsResponse : [];
    return rawChats.map((chat: any) => {
      const isGroup = chat.remoteJid?.includes('@g.us');
      if (isGroup) {
        const groupInfo = groupsMap.get(chat.remoteJid);
        if (groupInfo) {
          return {
            ...chat,
            name: groupInfo.subject, // Use group subject as name
            profilePicUrl: groupInfo.pictureUrl || chat.profilePicUrl,
            isGroup: true,
          };
        }
        return {
          ...chat,
          name: chat.pushName || 'Group',
          isGroup: true,
        };
      }
      // For direct chats
      return {
        ...chat,
        name: chat.pushName || formatDisplayName(chat.remoteJid),
        isGroup: false,
      };
    });
  }, [chatsResponse, groupsMap]);

  const isLoading = chatsLoading;
  const selectedChat = chats.find((c: any) => c.id === selectedChatId || c.remoteJid === selectedChatId);

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
          <ChatView
            instanceName={instanceName}
            chat={selectedChat}
          />
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
