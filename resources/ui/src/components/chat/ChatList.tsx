import { useState } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatListItem } from './ChatListItem';

interface ChatListProps {
  instanceName: string;
  chats: any[];
  selectedChatId: string | null;
  onSelectChat: (chatId: string) => void;
}

export function ChatList({ chats, selectedChatId, onSelectChat }: ChatListProps) {
  const [search, setSearch] = useState('');

  const filteredChats = chats.filter((chat: any) => {
    const name = chat.name || chat.pushName || chat.remoteJid || '';
    return name.toLowerCase().includes(search.toLowerCase());
  });

  // Sort by last message timestamp
  const sortedChats = [...filteredChats].sort((a: any, b: any) => {
    const aTime = a.lastMessageTimestamp || a.updatedAt || 0;
    const bTime = b.lastMessageTimestamp || b.updatedAt || 0;
    return bTime - aTime;
  });

  return (
    <div className="flex flex-col h-full border-r">
      {/* Search */}
      <div className="p-3 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search chats..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9"
          />
        </div>
      </div>

      {/* Chat List */}
      <ScrollArea className="flex-1">
        <div className="divide-y">
          {sortedChats.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              {search ? 'No chats found' : 'No chats yet'}
            </div>
          ) : (
            sortedChats.map((chat: any) => (
              <ChatListItem
                key={chat.id || chat.remoteJid}
                chat={chat}
                isSelected={selectedChatId === chat.id || selectedChatId === chat.remoteJid}
                onClick={() => onSelectChat(chat.id || chat.remoteJid)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
