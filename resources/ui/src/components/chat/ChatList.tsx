import { useState } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatListItem } from './ChatListItem';
import type { EvolutionChat } from '@/lib';

interface ChatListProps {
  instanceName: string;
  chats: EvolutionChat[];
  selectedChatId: string | null;
  onSelectChat: (chatId: string) => void;
}

export function ChatList({ chats, selectedChatId, onSelectChat }: ChatListProps) {
  const [search, setSearch] = useState('');

  const filteredChats = chats.filter((chat) => {
    const name = chat.name || chat.pushName || chat.remoteJid || '';
    return name.toLowerCase().includes(search.toLowerCase());
  });

  // Sort by last message timestamp (most recent first)
  // Chats without messages go to the bottom, sorted by updatedAt as tiebreaker
  const sortedChats = [...filteredChats].sort((a, b) => {
    // Use lastMessage.messageTimestamp if available (Unix timestamp in seconds)
    const aLastMsgTime = a.lastMessage?.messageTimestamp ? Number(a.lastMessage.messageTimestamp) * 1000 : 0;
    const bLastMsgTime = b.lastMessage?.messageTimestamp ? Number(b.lastMessage.messageTimestamp) * 1000 : 0;

    // If both have no messages, sort by updatedAt as tiebreaker (keeps them grouped at bottom)
    if (aLastMsgTime === 0 && bLastMsgTime === 0) {
      const aUpdated = a.updatedAt ? new Date(a.updatedAt).getTime() : 0;
      const bUpdated = b.updatedAt ? new Date(b.updatedAt).getTime() : 0;
      return bUpdated - aUpdated;
    }

    // Chats without messages go to bottom (use 0 instead of falling back to updatedAt)
    return bLastMsgTime - aLastMsgTime;
  });

  return (
    <div className="flex flex-col h-full bg-card">
      {/* Header */}
      <div className="px-4 py-3 bg-muted/50 border-b border-border">
        <h2 className="text-xl font-semibold text-foreground">Chats</h2>
      </div>

      {/* Search */}
      <div className="p-2 bg-muted/30">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search or start new chat"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 bg-background border-border rounded-lg"
          />
        </div>
      </div>

      {/* Chat List */}
      <ScrollArea className="flex-1">
        {sortedChats.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">{search ? 'No chats found' : 'No chats yet'}</div>
        ) : (
          sortedChats.map((chat) => (
            <ChatListItem
              key={chat.id || chat.remoteJid}
              chat={chat}
              isSelected={selectedChatId === chat.id || selectedChatId === chat.remoteJid}
              onClick={() => onSelectChat(chat.id || chat.remoteJid)}
            />
          ))
        )}
      </ScrollArea>
    </div>
  );
}
