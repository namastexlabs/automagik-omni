import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import {
  AlertCircle,
  Search,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Archive,
  Pin,
  Users,
  User,
  Hash,
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { formatRelativeTime, truncate } from '@/lib/utils';
import type { OmniChat, OmniChatType } from '@/lib/types';

export default function Chats() {
  const [selectedInstance, setSelectedInstance] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [chatTypeFilter, setChatTypeFilter] = useState<string>('all');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 50;

  // Fetch available instances
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100 }),
  });

  // Auto-select first instance if none selected
  if (!selectedInstance && instances && instances.length > 0) {
    setSelectedInstance(instances[0].name);
  }

  // Fetch chats for selected instance
  const {
    data: chatsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['chats', selectedInstance, page, searchQuery, chatTypeFilter, includeArchived],
    queryFn: () =>
      api.chats.list(selectedInstance, {
        page,
        page_size: pageSize,
        search_query: searchQuery || undefined,
        chat_type: chatTypeFilter !== 'all' ? (chatTypeFilter as any) : undefined,
        include_archived: includeArchived,
      }),
    enabled: !!selectedInstance,
  });

  const getChatTypeIcon = (chatType: OmniChatType) => {
    switch (chatType) {
      case 'direct':
        return <User className="h-4 w-4" />;
      case 'group':
        return <Users className="h-4 w-4" />;
      case 'channel':
        return <Hash className="h-4 w-4" />;
      case 'thread':
        return <MessageSquare className="h-4 w-4" />;
      default:
        return <MessageSquare className="h-4 w-4" />;
    }
  };

  const getChatTypeBadge = (chatType: OmniChatType) => {
    const colors: Record<OmniChatType, string> = {
      direct: 'gradient-primary',
      group: 'gradient-success',
      channel: 'gradient-info',
      thread: 'bg-secondary',
    };

    return (
      <Badge className={`${colors[chatType] || 'bg-secondary'} border-0 capitalize text-xs`}>
        {chatType}
      </Badge>
    );
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Chats"
          subtitle="View conversations across all channels"
          icon={<MessageSquare className="h-6 w-6 text-primary" />}
        />

        {/* Filters */}
        <div className="border-b border-border bg-card">
          <div className="px-8 py-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {/* Instance Selector */}
              <div className="space-y-2">
                <Label>Instance</Label>
                <Select value={selectedInstance} onValueChange={setSelectedInstance}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select instance" />
                  </SelectTrigger>
                  <SelectContent>
                    {instances?.map((instance) => (
                      <SelectItem key={instance.id} value={instance.name}>
                        {instance.name} ({instance.channel_type})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Search */}
              <div className="space-y-2 md:col-span-2">
                <Label>Search</Label>
                <form onSubmit={handleSearch} className="flex gap-2">
                  <Input
                    placeholder="Search chats..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <Button type="submit" variant="outline">
                    <Search className="h-4 w-4" />
                  </Button>
                </form>
              </div>

              {/* Chat Type Filter */}
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={chatTypeFilter} onValueChange={(value) => { setChatTypeFilter(value); setPage(1); }}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Types</SelectItem>
                    <SelectItem value="direct">Direct</SelectItem>
                    <SelectItem value="group">Group</SelectItem>
                    <SelectItem value="channel">Channel</SelectItem>
                    <SelectItem value="thread">Thread</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Include Archived */}
              <div className="space-y-2 flex items-end">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeArchived}
                    onChange={(e) => { setIncludeArchived(e.target.checked); setPage(1); }}
                    className="h-4 w-4 rounded border-border"
                  />
                  <span className="text-sm">Include archived</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {/* Error Alert */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2">
                    <div className="font-semibold">Error loading chats</div>
                    <div className="text-sm">
                      {error instanceof Error && error.message.includes('near "ON": syntax error') ? (
                        <>
                          <p className="mb-2">Evolution API database error detected.</p>
                          <p className="text-xs opacity-90">
                            This is a known issue with the Evolution API's Prisma SQLite query.
                            The Omni abstraction layer is working correctly, but the underlying
                            Evolution API needs to be updated to fix the SQL syntax error in the
                            chat listing query.
                          </p>
                        </>
                      ) : (
                        error.message || 'Unknown error'
                      )}
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            {/* No Instance Selected */}
            {!selectedInstance && instances && instances.length > 0 && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>Please select an instance to view chats</AlertDescription>
              </Alert>
            )}

            {/* No Instances Available */}
            {instances && instances.length === 0 && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  No instances available. Please create an instance first.
                </AlertDescription>
              </Alert>
            )}

            {/* Loading Skeletons */}
            {isLoading && (
              <div className="space-y-3">
                {[...Array(10)].map((_, i) => (
                  <Card key={i} className="border-border elevation-sm">
                    <CardContent className="py-4">
                      <div className="flex items-start space-x-4">
                        <Skeleton className="h-12 w-12 rounded-full" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-5 w-1/3" />
                          <Skeleton className="h-4 w-full" />
                        </div>
                        <Skeleton className="h-6 w-16" />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Empty State */}
            {chatsData && chatsData.chats.length === 0 && !error && (
              <Card className="border-border elevation-md">
                <CardContent className="pt-12 pb-12 text-center">
                  <div className="flex flex-col items-center space-y-4">
                    <div className="h-20 w-20 rounded-2xl bg-muted flex items-center justify-center">
                      <MessageSquare className="h-10 w-10 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-foreground mb-2">No chats found</p>
                      <p className="text-sm text-muted-foreground mb-2">
                        {searchQuery
                          ? 'Try adjusting your search query'
                          : 'No chats available for this instance'}
                      </p>
                      <p className="text-xs text-muted-foreground bg-yellow-50 dark:bg-yellow-950/20 p-3 rounded-lg border border-yellow-200 dark:border-yellow-900 mt-4 max-w-md mx-auto">
                        <strong>Note:</strong> If you have active chats but they're not showing,
                        this may be due to a known Evolution API database issue. The Omni system
                        is working correctly and returning an empty list as a safe fallback.
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Chat List */}
            {chatsData && chatsData.chats.length > 0 && (
              <>
                <div className="flex justify-between items-center">
                  <p className="text-sm text-muted-foreground">
                    Showing {chatsData.chats.length} of {chatsData.total_count} chats
                  </p>
                  <Badge variant="outline">
                    {chatsData.instance_name} ({chatsData.channel_type || 'all channels'})
                  </Badge>
                </div>

                <div className="space-y-2">
                  {chatsData.chats.map((chat: OmniChat) => (
                    <Card
                      key={chat.id}
                      className="group border-border elevation-sm hover:elevation-md transition-all hover-lift overflow-hidden bg-card cursor-pointer"
                    >
                      <CardContent className="py-4">
                        <div className="flex items-start space-x-4">
                          {/* Avatar */}
                          <div className="relative flex-shrink-0">
                            {chat.avatar_url ? (
                              <img
                                src={chat.avatar_url}
                                alt={chat.name}
                                className="h-12 w-12 rounded-full object-cover border-2 border-border"
                              />
                            ) : (
                              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center border-2 border-border">
                                {getChatTypeIcon(chat.chat_type)}
                              </div>
                            )}
                            {chat.unread_count && chat.unread_count > 0 && (
                              <div className="absolute -top-1 -right-1 h-5 w-5 rounded-full gradient-danger flex items-center justify-center text-xs font-bold text-white border-2 border-card">
                                {chat.unread_count > 9 ? '9+' : chat.unread_count}
                              </div>
                            )}
                          </div>

                          {/* Chat Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-semibold text-foreground truncate">{chat.name}</h3>
                              {getChatTypeBadge(chat.chat_type)}
                              {chat.is_pinned && <Pin className="h-3 w-3 text-primary" />}
                              {chat.is_archived && <Archive className="h-3 w-3 text-muted-foreground" />}
                              {chat.is_muted && (
                                <Badge variant="outline" className="text-xs">
                                  Muted
                                </Badge>
                              )}
                            </div>
                            {chat.description && (
                              <p className="text-sm text-muted-foreground mb-1">
                                {truncate(chat.description, 100)}
                              </p>
                            )}
                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                              {chat.participant_count && (
                                <span className="flex items-center gap-1">
                                  <Users className="h-3 w-3" />
                                  {chat.participant_count} members
                                </span>
                              )}
                              {chat.last_message_at && (
                                <span>Last message {formatRelativeTime(chat.last_message_at)}</span>
                              )}
                            </div>
                          </div>

                          {/* Timestamp */}
                          {chat.last_message_at && (
                            <div className="text-xs text-muted-foreground whitespace-nowrap">
                              {formatRelativeTime(chat.last_message_at)}
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Pagination */}
                {chatsData.total_count > pageSize && (
                  <div className="flex justify-center items-center gap-2 pt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
                    </Button>
                    <span className="text-sm text-muted-foreground px-4">
                      Page {page} of {Math.ceil(chatsData.total_count / pageSize)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!chatsData.has_more}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
