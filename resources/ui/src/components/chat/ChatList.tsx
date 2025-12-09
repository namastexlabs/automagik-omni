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
  const sortedChats = [...filteredChats].sort((a, b) => {
    const aTime = new Date(a.updatedAt || 0).getTime();
    const bTime = new Date(b.updatedAt || 0).getTime();
    return bTime - aTime;
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
