import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { api } from '@/lib/api';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { AlertCircle, Search, Users as UsersIcon, ChevronLeft, ChevronRight } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { formatRelativeTime } from '@/lib/utils';
import type { OmniContact, OmniContactStatus } from '@/lib/types';

export default function Contacts() {
  const [selectedInstance, setSelectedInstance] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
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

  // Fetch contacts for selected instance
  const {
    data: contactsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['contacts', selectedInstance, page, searchQuery, statusFilter],
    queryFn: () =>
      api.contacts.list(selectedInstance, {
        page,
        page_size: pageSize,
        search_query: searchQuery || undefined,
        status_filter: statusFilter !== 'all' ? statusFilter : undefined,
      }),
    enabled: !!selectedInstance,
  });

  const getStatusColor = (status: OmniContactStatus): string => {
    switch (status) {
      case 'online':
        return 'bg-success';
      case 'offline':
        return 'bg-muted';
      case 'away':
        return 'bg-warning';
      case 'dnd':
        return 'bg-destructive';
      default:
        return 'bg-muted';
    }
  };

  const getStatusBadge = (status: OmniContactStatus) => {
    switch (status) {
      case 'online':
        return <Badge className="gradient-success border-0 capitalize">{status}</Badge>;
      case 'offline':
        return <Badge variant="outline" className="capitalize">{status}</Badge>;
      case 'away':
        return <Badge className="gradient-warning border-0 capitalize">{status}</Badge>;
      case 'dnd':
        return <Badge className="gradient-danger border-0 capitalize">Do Not Disturb</Badge>;
      default:
        return <Badge variant="outline" className="capitalize">{status}</Badge>;
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1); // Reset to first page on new search
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Contacts"
          subtitle="View contacts across all channels"
          icon={<UsersIcon className="h-6 w-6 text-primary" />}
        />

        {/* Filters */}
        <div className="border-b border-border bg-card">
          <div className="px-8 py-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                    placeholder="Search contacts..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  <Button type="submit" variant="outline">
                    <Search className="h-4 w-4" />
                  </Button>
                </form>
              </div>

              {/* Status Filter */}
              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={statusFilter} onValueChange={(value) => { setStatusFilter(value); setPage(1); }}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="online">Online</SelectItem>
                    <SelectItem value="offline">Offline</SelectItem>
                    <SelectItem value="away">Away</SelectItem>
                    <SelectItem value="dnd">Do Not Disturb</SelectItem>
                  </SelectContent>
                </Select>
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
                  Error loading contacts: {error instanceof Error ? error.message : 'Unknown error'}
                </AlertDescription>
              </Alert>
            )}

            {/* No Instance Selected */}
            {!selectedInstance && instances && instances.length > 0 && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>Please select an instance to view contacts</AlertDescription>
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
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {[...Array(9)].map((_, i) => (
                  <Card key={i} className="border-border elevation-sm">
                    <CardContent className="pt-6">
                      <div className="flex items-start space-x-4">
                        <Skeleton className="h-12 w-12 rounded-full" />
                        <div className="flex-1 space-y-2">
                          <Skeleton className="h-5 w-3/4" />
                          <Skeleton className="h-4 w-1/2" />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Empty State */}
            {contactsData && contactsData.contacts.length === 0 && (
              <Card className="border-border elevation-md">
                <CardContent className="pt-12 pb-12 text-center">
                  <div className="flex flex-col items-center space-y-4">
                    <div className="h-20 w-20 rounded-2xl bg-muted flex items-center justify-center">
                      <UsersIcon className="h-10 w-10 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-foreground mb-2">No contacts found</p>
                      <p className="text-sm text-muted-foreground">
                        {searchQuery
                          ? 'Try adjusting your search query'
                          : 'No contacts available for this instance'}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Contact Cards */}
            {contactsData && contactsData.contacts.length > 0 && (
              <>
                <div className="flex justify-between items-center">
                  <p className="text-sm text-muted-foreground">
                    Showing {contactsData.contacts.length} of {contactsData.total_count} contacts
                  </p>
                  <Badge variant="outline">
                    {contactsData.instance_name} ({contactsData.channel_type || 'all channels'})
                  </Badge>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {contactsData.contacts.map((contact: OmniContact) => (
                    <Card
                      key={contact.id}
                      className="group border-border elevation-sm hover:elevation-md transition-all hover-lift overflow-hidden bg-card"
                    >
                      <CardContent className="pt-6">
                        <div className="flex items-start space-x-4">
                          {/* Avatar */}
                          <div className="relative">
                            {contact.avatar_url ? (
                              <img
                                src={contact.avatar_url}
                                alt={contact.name}
                                className="h-12 w-12 rounded-full object-cover border-2 border-border"
                              />
                            ) : (
                              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center border-2 border-border">
                                <span className="text-lg font-semibold text-primary">
                                  {contact.name.charAt(0).toUpperCase()}
                                </span>
                              </div>
                            )}
                            {/* Status Indicator */}
                            <div
                              className={`absolute bottom-0 right-0 h-3 w-3 rounded-full border-2 border-card ${getStatusColor(
                                contact.status
                              )}`}
                            />
                          </div>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-semibold text-foreground truncate">{contact.name}</h3>
                              {contact.is_verified && (
                                <Badge className="gradient-primary text-xs border-0">✓</Badge>
                              )}
                              {contact.is_business && (
                                <Badge variant="outline" className="text-xs">
                                  Business
                                </Badge>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground mb-2">ID: {contact.id}</p>
                            <div className="flex items-center justify-between">
                              {getStatusBadge(contact.status)}
                              {contact.last_seen && (
                                <span className="text-xs text-muted-foreground">
                                  {formatRelativeTime(contact.last_seen)}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Pagination */}
                {contactsData.total_count > pageSize && (
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
                      Page {page} of {Math.ceil(contactsData.total_count / pageSize)}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => p + 1)}
                      disabled={!contactsData.has_more}
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
