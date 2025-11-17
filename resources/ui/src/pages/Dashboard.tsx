import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { DashboardLayout } from '@/components/DashboardLayout';
import { MetricCard } from '@/components/MetricCard';
import { Activity, MessageSquare, Users, Zap } from 'lucide-react';

export default function Dashboard() {
  const { data: instances, isLoading, error } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_status: true }),
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'connected':
        return <Badge className="bg-green-600">Connected</Badge>;
      case 'close':
      case 'disconnected':
        return <Badge variant="destructive">Disconnected</Badge>;
      case 'connecting':
        return <Badge variant="secondary">Connecting</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  // Calculate metrics
  const totalInstances = instances?.length || 0;
  const activeInstances = instances?.filter(i => i.is_active).length || 0;
  const channelTypes = new Set(instances?.map(i => i.channel_type)).size || 0;
  const connectedInstances = instances?.filter(i =>
    i.evolution_status?.state?.toLowerCase() === 'open'
  ).length || 0;

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="border-b">
          <div className="flex h-16 items-center px-8">
            <h1 className="text-2xl font-bold">Dashboard</h1>
            <div className="ml-auto flex items-center space-x-4">
              <div className="text-sm">
                <span className="text-muted-foreground">API Status: </span>
                <span className={health?.status === 'healthy' ? 'text-green-600 font-medium' : 'text-red-600 font-medium'}>
                  {health?.status || 'checking...'}
                </span>
              </div>
              <Button>Create Instance</Button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto p-8">
          <div className="space-y-8">
            {/* Metrics Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Total Instances"
                value={totalInstances}
                description="All configured instances"
                icon={Activity}
              />
              <MetricCard
                title="Active Instances"
                value={activeInstances}
                description="Currently running"
                icon={Zap}
              />
              <MetricCard
                title="Connected"
                value={connectedInstances}
                description="Successfully connected"
                icon={MessageSquare}
              />
              <MetricCard
                title="Channels"
                value={channelTypes}
                description="Different channel types"
                icon={Users}
              />
            </div>

            {/* Instances List */}
            <div>
              <h2 className="text-xl font-semibold mb-4">Instances</h2>

              {isLoading && (
                <Card>
                  <CardContent className="pt-6">
                    <p className="text-center text-muted-foreground">Loading instances...</p>
                  </CardContent>
                </Card>
              )}

              {error && (
                <Card className="border-destructive">
                  <CardContent className="pt-6">
                    <p className="text-destructive">
                      Error loading instances: {error instanceof Error ? error.message : 'Unknown error'}
                    </p>
                  </CardContent>
                </Card>
              )}

              {instances && instances.length === 0 && (
                <Card>
                  <CardContent className="pt-6 text-center">
                    <p className="text-muted-foreground mb-4">No instances found</p>
                    <Button>Create Your First Instance</Button>
                  </CardContent>
                </Card>
              )}

              {instances && instances.length > 0 && (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {instances.map((instance) => (
                    <Card key={instance.id} className="hover:shadow-md transition-shadow">
                      <CardHeader>
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <CardTitle className="text-lg">{instance.name}</CardTitle>
                            <CardDescription className="capitalize">
                              {instance.channel_type}
                            </CardDescription>
                          </div>
                          {getStatusBadge(instance.evolution_status?.state || (instance.is_active ? 'active' : 'inactive'))}
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-2 text-sm">
                          {instance.profile_name && (
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Profile:</span>
                              <span className="font-medium">{instance.profile_name}</span>
                            </div>
                          )}
                          {instance.automagik_instance_name && (
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Agent:</span>
                              <span className="font-medium">{instance.automagik_instance_name}</span>
                            </div>
                          )}
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Created:</span>
                            <span>{new Date(instance.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                        <div className="mt-4 flex space-x-2">
                          <Button variant="outline" size="sm" className="flex-1">
                            View
                          </Button>
                          <Button variant="outline" size="sm" className="flex-1">
                            Manage
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
