import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { api, formatDateTime } from '@/lib';
import type { User, InstanceConfig } from '@/lib';
import {
  Users as UsersIcon,
  Search,
  MessageSquare,
  Clock,
  Trash2,
  GitMerge,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react';

// Channel icons/badges
const ChannelBadge = ({ provider }: { provider: string }) => {
  const config: Record<string, { color: string; label: string; icon: string }> = {
    whatsapp: { color: 'bg-green-500', label: 'WhatsApp', icon: '📱' },
    discord: { color: 'bg-indigo-500', label: 'Discord', icon: '💬' },
  };
  const { color, label, icon } = config[provider] || { color: 'bg-gray-500', label: provider, icon: '🔗' };

  return (
    <Badge variant="secondary" className={`${color} text-white text-xs`}>
      {icon} {label}
    </Badge>
  );
};

// User card component
const UserCard = ({
  user,
  onClick,
  isSelected,
  potentialMatches,
}: {
  user: User;
  onClick: () => void;
  isSelected: boolean;
  potentialMatches?: User[];
}) => {
  // Get unique providers from external_ids, falling back to channel_type
  const providers = user.external_ids?.map((e) => e.provider) || [];
  const uniqueProviders = [...new Set([user.channel_type, ...providers])].filter(Boolean);

  return (
    <Card
      className={`cursor-pointer transition-all hover:shadow-md ${isSelected ? 'ring-2 ring-primary' : ''}`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-medium truncate">{user.display_name || 'Unknown User'}</h3>
              {user.last_seen_at && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDateTime(user.last_seen_at)}
                </span>
              )}
            </div>

            {/* Show phone or Discord info based on channel type */}
            {user.channel_type === 'discord'
              ? user.discord_username && (
                  <p className="text-xs text-muted-foreground mb-1 font-mono">💬 @{user.discord_username}</p>
                )
              : user.phone_number &&
                user.phone_number !== user.display_name && (
                  <p className="text-xs text-muted-foreground mb-1 font-mono">📱 {user.phone_number}</p>
                )}

            <div className="flex flex-wrap gap-1 mb-2">
              {uniqueProviders.map((provider) => (
                <ChannelBadge key={provider} provider={provider} />
              ))}
            </div>

            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <MessageSquare className="h-3 w-3" />
                {user.message_count || 0} messages
              </span>
              <span>• {user.instance_name}</span>
            </div>

            {/* Potential matches warning */}
            {potentialMatches && potentialMatches.length > 0 && (
              <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-950 rounded-md border border-amber-200 dark:border-amber-800">
                <div className="flex items-center gap-1 text-amber-700 dark:text-amber-400 text-xs">
                  <AlertTriangle className="h-3 w-3" />
                  <span>
                    {potentialMatches.length} potential match{potentialMatches.length > 1 ? 'es' : ''}
                  </span>
                </div>
                <div className="mt-1 text-xs text-amber-600 dark:text-amber-500">
                  {potentialMatches.slice(0, 3).map((m) => {
                    // Determine what to show: provider if different, or instance/phone
                    const provider = m.external_ids?.[0]?.provider;
                    const identifier = provider
                      ? provider
                      : m.instance_name !== user.instance_name
                        ? m.instance_name
                        : m.phone_number || 'other account';
                    return (
                      <div key={m.id} className="truncate">
                        "{m.display_name}" ({identifier})
                      </div>
                    );
                  })}
                  {potentialMatches.length > 3 && (
                    <div className="text-muted-foreground">+{potentialMatches.length - 3} more</div>
                  )}
                </div>
              </div>
            )}
          </div>
          <ChevronRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />
        </div>
      </CardContent>
    </Card>
  );
};

// User detail panel
const UserDetailPanel = ({
  user,
  isOpen,
  onClose,
  onMerge,
  onDelete,
  allUsers,
}: {
  user: User | null;
  isOpen: boolean;
  onClose: () => void;
  onMerge: (targetUser: User, sourceUser: User) => void;
  onDelete: (user: User) => void;
  allUsers: User[];
}) => {
  const [isMergeDialogOpen, setIsMergeDialogOpen] = useState(false);
  const [selectedMergeUser, setSelectedMergeUser] = useState<User | null>(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  if (!user) return null;

  // Find potential users to merge (different users, same instance or linkable)
  const mergeableUsers = allUsers.filter((u) => u.id !== user.id);

  return (
    <>
      <Sheet open={isOpen} onOpenChange={onClose}>
        <SheetContent className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <UsersIcon className="h-5 w-5" />
              {user.display_name || 'Unknown User'}
            </SheetTitle>
            <SheetDescription>User ID: {user.id.slice(0, 8)}...</SheetDescription>
          </SheetHeader>

          <ScrollArea className="h-[calc(100vh-200px)] mt-6">
            <div className="space-y-6 pr-4">
              {/* Connected Channels */}
              <div>
                <h4 className="text-sm font-medium mb-3">Connected Channels</h4>
                <div className="space-y-2">
                  {user.external_ids && user.external_ids.length > 0 ? (
                    user.external_ids.map((ext) => (
                      <Card key={ext.id} className="p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <ChannelBadge provider={ext.provider} />
                            <p className="text-sm mt-1 font-mono">{ext.external_id}</p>
                            {ext.instance_name && <p className="text-xs text-muted-foreground">{ext.instance_name}</p>}
                          </div>
                        </div>
                      </Card>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No external IDs linked</p>
                  )}
                </div>
              </div>

              <Separator />

              {/* User Info */}
              <div>
                <h4 className="text-sm font-medium mb-3">User Info</h4>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-24">Channel:</span>
                    <ChannelBadge provider={user.channel_type} />
                  </div>
                  {user.channel_type === 'discord'
                    ? user.discord_username && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-24">Username:</span>
                          <span className="text-sm font-mono">@{user.discord_username}</span>
                        </div>
                      )
                    : user.phone_number && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-24">Phone:</span>
                          <span className="text-sm font-mono">{user.phone_number}</span>
                        </div>
                      )}
                </div>
              </div>

              <Separator />

              {/* Stats */}
              <div>
                <h4 className="text-sm font-medium mb-3">Activity</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-2xl font-bold">{user.message_count || 0}</p>
                    <p className="text-xs text-muted-foreground">Total Messages</p>
                  </div>
                  <div>
                    <p className="text-sm">{user.last_seen_at ? formatDateTime(user.last_seen_at) : 'Never'}</p>
                    <p className="text-xs text-muted-foreground">Last Seen</p>
                  </div>
                  <div>
                    <p className="text-sm">{user.created_at ? formatDateTime(user.created_at) : 'Unknown'}</p>
                    <p className="text-xs text-muted-foreground">First Seen</p>
                  </div>
                  <div>
                    <p className="text-sm truncate">{user.instance_name}</p>
                    <p className="text-xs text-muted-foreground">Instance</p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Actions */}
              <div className="space-y-2">
                <Button variant="outline" className="w-full justify-start" onClick={() => setIsMergeDialogOpen(true)}>
                  <GitMerge className="h-4 w-4 mr-2" />
                  Merge with Another User
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start text-destructive hover:text-destructive"
                  onClick={() => setIsDeleteDialogOpen(true)}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete User
                </Button>
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Merge Dialog */}
      <Dialog open={isMergeDialogOpen} onOpenChange={setIsMergeDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Merge Users</DialogTitle>
            <DialogDescription>
              Select a user to merge into "{user.display_name}". The selected user will be deleted and their channels
              will be linked to this user.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Primary user (target) */}
            <div>
              <p className="text-sm font-medium mb-2">Keep this user (primary):</p>
              <Card className="p-3 bg-primary/5 border-primary">
                <div className="flex items-center gap-2">
                  <UsersIcon className="h-4 w-4" />
                  <span className="font-medium">{user.display_name}</span>
                  <div className="flex gap-1 ml-auto">
                    {[...new Set(user.external_ids?.map((e) => e.provider) || [])].map((p) => (
                      <ChannelBadge key={p} provider={p} />
                    ))}
                  </div>
                </div>
              </Card>
            </div>

            {/* Select user to merge */}
            <div>
              <p className="text-sm font-medium mb-2">Merge and delete this user:</p>
              <ScrollArea className="h-[200px] border rounded-md p-2">
                <div className="space-y-2">
                  {mergeableUsers.map((u) => (
                    <Card
                      key={u.id}
                      className={`p-3 cursor-pointer transition-all hover:bg-accent ${
                        selectedMergeUser?.id === u.id ? 'ring-2 ring-destructive bg-destructive/5' : ''
                      }`}
                      onClick={() => setSelectedMergeUser(u)}
                    >
                      <div className="flex items-center gap-2">
                        <UsersIcon className="h-4 w-4" />
                        <span>{u.display_name || 'Unknown'}</span>
                        <span className="text-xs text-muted-foreground">({u.message_count || 0} msgs)</span>
                        <div className="flex gap-1 ml-auto">
                          {[...new Set(u.external_ids?.map((e) => e.provider) || [])].map((p) => (
                            <ChannelBadge key={p} provider={p} />
                          ))}
                        </div>
                      </div>
                    </Card>
                  ))}
                  {mergeableUsers.length === 0 && (
                    <p className="text-sm text-muted-foreground text-center py-4">No other users to merge</p>
                  )}
                </div>
              </ScrollArea>
            </div>

            {/* Preview */}
            {selectedMergeUser && (
              <div className="bg-muted p-3 rounded-md">
                <p className="text-sm font-medium mb-2">After merge:</p>
                <div className="flex items-center gap-2">
                  <UsersIcon className="h-4 w-4" />
                  <span>{user.display_name}</span>
                  <div className="flex gap-1 ml-2">
                    {[
                      ...new Set([
                        ...(user.external_ids?.map((e) => e.provider) || []),
                        ...(selectedMergeUser.external_ids?.map((e) => e.provider) || []),
                      ]),
                    ].map((p) => (
                      <ChannelBadge key={p} provider={p} />
                    ))}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {(user.message_count || 0) + (selectedMergeUser.message_count || 0)} messages combined
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsMergeDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!selectedMergeUser}
              onClick={() => {
                if (selectedMergeUser) {
                  onMerge(user, selectedMergeUser);
                  setIsMergeDialogOpen(false);
                  setSelectedMergeUser(null);
                }
              }}
            >
              <GitMerge className="h-4 w-4 mr-2" />
              Merge Users
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete User</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{user.display_name}"? This will remove all their linked channels and
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                onDelete(user);
                setIsDeleteDialogOpen(false);
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

// Potential match finding algorithm (conservative)
// Finds users who might be the same person across different channels/instances
function findPotentialMatches(user: User, allUsers: User[]): User[] {
  const matches: User[] = [];
  const userName = (user.display_name || '').toLowerCase().trim();

  if (!userName || userName === 'unknown user') return [];

  // Get user's providers (channels)
  const userProviders = new Set(user.external_ids?.map((e) => e.provider) || []);
  // If no external_ids, infer from instance (WhatsApp if has whatsapp_jid)
  if (userProviders.size === 0 && user.whatsapp_jid) {
    userProviders.add('whatsapp');
  }

  for (const other of allUsers) {
    if (other.id === user.id) continue;

    // Skip if same instance AND same phone (definitely same user record)
    if (user.instance_name === other.instance_name && user.phone_number === other.phone_number) {
      continue;
    }

    // Get other's providers
    const otherProviders = new Set(other.external_ids?.map((e) => e.provider) || []);
    if (otherProviders.size === 0 && other.whatsapp_jid) {
      otherProviders.add('whatsapp');
    }

    // For cross-channel matching, prefer users on DIFFERENT channels
    // For same channel, only match if different instances (could be same person with different accounts)
    const sameChannel = [...userProviders].some((p) => otherProviders.has(p));
    const sameInstance = user.instance_name === other.instance_name;

    // Skip if same channel AND same instance (would be duplicate records, not cross-channel)
    if (sameChannel && sameInstance) continue;

    const otherName = (other.display_name || '').toLowerCase().trim();
    if (!otherName || otherName === 'unknown user') continue;

    // Conservative matching criteria:
    // 1. Exact name match (case insensitive)
    // 2. Name starts with same 5+ characters
    // 3. Name contains the other as a substring (if both > 4 chars)
    const isExactMatch = userName === otherName;
    const startsWithSame =
      userName.length >= 5 && otherName.length >= 5 && userName.slice(0, 5) === otherName.slice(0, 5);
    const isSubstring =
      userName.length > 4 && otherName.length > 4 && (userName.includes(otherName) || otherName.includes(userName));

    if (isExactMatch || startsWithSame || isSubstring) {
      matches.push(other);
    }
  }

  return matches;
}

export default function Users() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterProvider, setFilterProvider] = useState<string>('all');
  const [filterInstance, setFilterInstance] = useState<string>('all');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Fetch users
  const {
    data: usersData,
    isLoading: usersLoading,
    error: usersError,
  } = useQuery({
    queryKey: ['users', filterProvider, filterInstance],
    queryFn: () =>
      api.users.list({
        provider: filterProvider === 'all' ? undefined : filterProvider,
        instance_name: filterInstance === 'all' ? undefined : filterInstance,
        limit: 500,
      }),
  });

  // Fetch instances for filter dropdown
  const { data: instances } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list(),
  });

  // Merge mutation
  const mergeMutation = useMutation({
    mutationFn: ({ targetId, sourceId }: { targetId: string; sourceId: string }) => api.users.merge(targetId, sourceId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success(`Merged successfully: ${data.external_ids_transferred} channels transferred`);
      setSelectedUser(null);
      setIsDetailOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to merge users');
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (userId: string) => api.users.delete(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User deleted');
      setSelectedUser(null);
      setIsDetailOpen(false);
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to delete user');
    },
  });

  // Filter users by search
  const filteredUsers = useMemo(() => {
    if (!usersData?.users) return [];

    return usersData.users.filter((user) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        user.display_name?.toLowerCase().includes(query) ||
        user.phone_number?.toLowerCase().includes(query) ||
        user.external_ids?.some((e) => e.external_id.toLowerCase().includes(query))
      );
    });
  }, [usersData?.users, searchQuery]);

  // Compute potential matches for each user
  const userMatchesMap = useMemo(() => {
    const map = new Map<string, User[]>();
    if (!usersData?.users) return map;

    for (const user of usersData.users) {
      const matches = findPotentialMatches(user, usersData.users);
      if (matches.length > 0) {
        map.set(user.id, matches);
      }
    }
    return map;
  }, [usersData?.users]);

  // Get unique providers from users
  const availableProviders = useMemo(() => {
    if (!usersData?.users) return [];
    const providers = new Set<string>();
    for (const user of usersData.users) {
      for (const ext of user.external_ids || []) {
        providers.add(ext.provider);
      }
    }
    return [...providers];
  }, [usersData?.users]);

  const handleMerge = (targetUser: User, sourceUser: User) => {
    mergeMutation.mutate({ targetId: targetUser.id, sourceId: sourceUser.id });
  };

  const handleDelete = (user: User) => {
    deleteMutation.mutate(user.id);
  };

  const handleUserClick = (user: User) => {
    setSelectedUser(user);
    setIsDetailOpen(true);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Users"
          subtitle="Manage user identities across channels"
          icon={<UsersIcon className="h-6 w-6 text-primary" />}
        />

        <div className="flex-1 overflow-hidden p-6">
          {/* Filters */}
          <div className="flex flex-wrap gap-4 mb-6">
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, phone, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            <Select value={filterProvider} onValueChange={setFilterProvider}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                {availableProviders.map((provider) => (
                  <SelectItem key={provider} value={provider}>
                    {provider.charAt(0).toUpperCase() + provider.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filterInstance} onValueChange={setFilterInstance}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Instance" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Instances</SelectItem>
                {instances?.map((instance: InstanceConfig) => (
                  <SelectItem key={instance.name} value={instance.name}>
                    {instance.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Stats */}
          <div className="flex gap-4 mb-6">
            <Badge variant="outline" className="text-sm py-1 px-3">
              {usersData?.total || 0} Total Users
            </Badge>
            <Badge variant="outline" className="text-sm py-1 px-3">
              {userMatchesMap.size} With Potential Matches
            </Badge>
          </div>

          {/* Users Grid */}
          {usersLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-4">
                    <Skeleton className="h-4 w-3/4 mb-2" />
                    <Skeleton className="h-3 w-1/2 mb-2" />
                    <Skeleton className="h-3 w-1/3" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : usersError ? (
            <Card>
              <CardContent className="p-6 text-center text-destructive">
                Failed to load users: {(usersError as Error).message}
              </CardContent>
            </Card>
          ) : filteredUsers.length === 0 ? (
            <Card>
              <CardContent className="p-6 text-center text-muted-foreground">
                {searchQuery ? 'No users match your search' : 'No users found'}
              </CardContent>
            </Card>
          ) : (
            <ScrollArea className="h-[calc(100vh-320px)]">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pr-4">
                {filteredUsers.map((user) => (
                  <UserCard
                    key={user.id}
                    user={user}
                    onClick={() => handleUserClick(user)}
                    isSelected={selectedUser?.id === user.id}
                    potentialMatches={userMatchesMap.get(user.id)}
                  />
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
      </div>

      {/* User Detail Panel */}
      <UserDetailPanel
        user={selectedUser}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedUser(null);
        }}
        onMerge={handleMerge}
        onDelete={handleDelete}
        allUsers={usersData?.users || []}
      />
    </DashboardLayout>
  );
}
