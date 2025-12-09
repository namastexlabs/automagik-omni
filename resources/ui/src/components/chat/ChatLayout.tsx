import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, MessageSquare, AlertCircle, Play } from 'lucide-react';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ChatList } from './ChatList';
import { ChatView } from './ChatView';
import { api } from '@/lib';
import type { EvolutionChat, EvolutionGroup } from '@/lib';

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
  const queryClient = useQueryClient();

  // Mutation to start Evolution service
  const startEvolutionMutation = useMutation({
    mutationFn: () => api.gateway.startChannel('evolution'),
    onSuccess: () => {
      // Wait a moment for Evolution to fully start, then refetch
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['chats', instanceName] });
        queryClient.invalidateQueries({ queryKey: ['groups', instanceName] });
      }, 2000);
    },
  });

  // Fetch chats
  const {
    data: chatsResponse,
    isLoading: chatsLoading,
    isError: chatsError,
    error: chatsErrorData,
    refetch: refetchChats,
  } = useQuery<EvolutionChat[]>({
    queryKey: ['chats', instanceName],
    queryFn: () => api.evolution.findChats(instanceName),
    refetchInterval: 30000,
    retry: false, // Don't retry on Evolution errors
  });

  // Fetch groups to get proper group names
  const {
    data: groupsResponse,
    isLoading: groupsLoading,
    isError: groupsError,
  } = useQuery<EvolutionGroup[]>({
    queryKey: ['groups', instanceName],
    queryFn: () => api.evolution.fetchAllGroups(instanceName),
    refetchInterval: 60000,
    retry: false, // Don't retry on Evolution errors
  });

  // Create a map of group IDs to group info
  const groupsMap = useMemo(() => {
    const map = new Map<string, EvolutionGroup>();
    if (Array.isArray(groupsResponse)) {
      groupsResponse.forEach((group) => {
        if (group.id) {
          map.set(group.id, group);
        }
      });
    }
    return map;
  }, [groupsResponse]);

  // Merge chats with group info and filter out empty metadata-only entries
  const chats = useMemo(() => {
    const rawChats: EvolutionChat[] = Array.isArray(chatsResponse) ? chatsResponse : [];
    return rawChats
      .map((chat) => {
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
      })
      .filter((chat) => {
        // Filter out empty LID entries (no name and no messages)
        // These are WhatsApp metadata entries for contacts that haven't been messaged yet
        const isLID = chat.remoteJid?.includes('@lid');
        if (isLID && !chat.pushName && !chat.lastMessage) {
          return false; // Hide empty LID entries
        }
        return true;
      });
  }, [chatsResponse, groupsMap]);

  const isLoading = chatsLoading || groupsLoading;
  const hasEvolutionError = chatsError || groupsError;
  const selectedChat = chats.find((c) => c.id === selectedChatId || c.remoteJid === selectedChatId);

  // Handle Evolution service not running (500/503 errors)
  if (hasEvolutionError && !isLoading) {
    const isStarting = startEvolutionMutation.isPending;
    const justStarted = startEvolutionMutation.isSuccess;

    return (
      <div className="flex items-center justify-center h-full bg-background">
        <div className="max-w-md text-center space-y-4">
          <Alert variant={justStarted ? 'default' : 'destructive'}>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>{justStarted ? 'Starting WhatsApp Service...' : 'WhatsApp Service Not Running'}</AlertTitle>
            <AlertDescription>
              {justStarted
                ? 'Please wait while the service starts. This may take a few seconds.'
                : 'The WhatsApp service needs to be started to load your chats.'}
            </AlertDescription>
          </Alert>

          {justStarted ? (
            <div className="flex items-center justify-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Connecting...</span>
            </div>
          ) : (
            <Button onClick={() => startEvolutionMutation.mutate()} disabled={isStarting} className="gap-2">
              {isStarting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Start WhatsApp Service
                </>
              )}
            </Button>
          )}
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
