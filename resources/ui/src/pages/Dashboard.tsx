import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { DashboardLayout } from '@/components/DashboardLayout';
import { MetricCard } from '@/components/MetricCard';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Activity, MessageSquare, Users, Zap, Plus, Eye, Settings as SettingsIcon, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const { data: instances, isLoading, error } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_status: true }),
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000,
  });

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'connected':
        return <Badge className="gradient-success border-0">Connected</Badge>;
      case 'close':
      case 'disconnected':
        return <Badge className="gradient-danger border-0">Disconnected</Badge>;
      case 'connecting':
        return <Badge className="gradient-warning border-0">Connecting</Badge>;
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
        <div className="border-b border-border bg-card">
          <div className="flex h-20 items-center px-8">
            <h1 className="text-2xl font-bold text-foreground">
              Dashboard
            </h1>
            <div className="ml-auto flex items-center space-x-3">
              <div className="px-4 py-2 bg-muted rounded-lg elevation-sm border border-border">
                <span className="text-xs text-muted-foreground">API Status: </span>
                <span className={`text-sm font-semibold ${health?.status === 'healthy' ? 'text-success' : 'text-destructive'}`}>
                  {health?.status === 'healthy' ? '● Online' : '● Offline'}
                </span>
              </div>
              <ThemeToggle />
              <Button className="gradient-primary elevation-md hover:elevation-lg transition-all hover-lift">
                <Plus className="h-4 w-4 mr-2" />
                New Instance
              </Button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-8 animate-fade-in">
            {/* Metrics Grid */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Total Instances"
                value={totalInstances}
                description="All configured instances"
                icon={Activity}
                gradient="from-purple-500 to-indigo-500"
                trend={{ value: 12, isPositive: true }}
              />
              <MetricCard
                title="Active Now"
                value={activeInstances}
                description="Currently running"
                icon={Zap}
                gradient="from-blue-500 to-cyan-500"
                trend={{ value: 8, isPositive: true }}
              />
              <MetricCard
                title="Connected"
                value={connectedInstances}
                description="Successfully connected"
                icon={MessageSquare}
                gradient="from-green-500 to-emerald-500"
              />
              <MetricCard
                title="Channels"
                value={channelTypes}
                description="Different platforms"
                icon={Users}
                gradient="from-orange-500 to-pink-500"
              />
            </div>

            {/* Instances Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold flex items-center gap-2 text-foreground">
                    <TrendingUp className="h-6 w-6 text-primary" />
                    Active Instances
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1">Manage your messaging channels</p>
                </div>
                <Button variant="outline" className="elevation-sm hover:elevation-md hover-lift">
                  View All
                </Button>
              </div>

              {isLoading && (
                <Card className="border-border elevation-md">
                  <CardContent className="pt-12 pb-12">
                    <div className="flex flex-col items-center justify-center space-y-4">
                      <div className="h-12 w-12 rounded-full border-4 border-primary/20 border-t-primary animate-spin"></div>
                      <p className="text-muted-foreground">Loading instances...</p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {error && (
                <Card className="border-destructive elevation-md bg-destructive/5">
                  <CardContent className="pt-6">
                    <p className="text-destructive font-medium">
                      Error loading instances: {error instanceof Error ? error.message : 'Unknown error'}
                    </p>
                  </CardContent>
                </Card>
              )}

              {instances && instances.length === 0 && (
                <Card className="border-border elevation-md bg-gradient-to-br from-primary/5 to-primary/10">
                  <CardContent className="pt-12 pb-12 text-center">
                    <div className="flex flex-col items-center space-y-4">
                      <div className="h-20 w-20 rounded-2xl gradient-primary flex items-center justify-center elevation-lg">
                        <Plus className="h-10 w-10 text-primary-foreground" />
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-foreground mb-2">No instances yet</p>
                        <p className="text-sm text-muted-foreground mb-6">Get started by creating your first messaging instance</p>
                      </div>
                      <Button className="gradient-primary elevation-md hover:elevation-lg hover-lift">
                        <Plus className="h-4 w-4 mr-2" />
                        Create First Instance
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {instances && instances.length > 0 && (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {instances.map((instance) => (
                    <Card key={instance.id} className="group border-border elevation-md hover:elevation-lg transition-all hover-lift overflow-hidden bg-card">
                      <CardHeader className="relative">
                        <div className="flex justify-between items-start">
                          <div className="flex-1 space-y-1">
                            <CardTitle className="text-xl flex items-center gap-2 text-foreground">
                              {instance.name}
                              {instance.is_default && (
                                <Badge className="gradient-primary text-xs border-0">Default</Badge>
                              )}
                            </CardTitle>
                            <CardDescription className="capitalize flex items-center gap-2">
                              <span className="h-2 w-2 rounded-full bg-primary"></span>
                              {instance.channel_type}
                            </CardDescription>
                          </div>
                          {getStatusBadge(instance.evolution_status?.state || (instance.is_active ? 'active' : 'inactive'))}
                        </div>
                      </CardHeader>

                      <CardContent className="relative space-y-4">
                        <div className="space-y-2 text-sm">
                          {instance.profile_name && (
                            <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                              <span className="text-muted-foreground">Profile</span>
                              <span className="font-medium text-foreground">{instance.profile_name}</span>
                            </div>
                          )}
                          {instance.automagik_instance_name && (
                            <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                              <span className="text-muted-foreground">Agent</span>
                              <span className="font-medium text-foreground">{instance.automagik_instance_name}</span>
                            </div>
                          )}
                          <div className="flex justify-between items-center p-3 bg-muted rounded-lg border border-border">
                            <span className="text-muted-foreground">Created</span>
                            <span className="font-medium text-foreground">{new Date(instance.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>

                        <div className="flex gap-2 pt-2">
                          <Button variant="outline" size="sm" className="flex-1 hover:bg-primary/10 hover:text-primary hover:border-primary transition-colors">
                            <Eye className="h-4 w-4 mr-1" />
                            View
                          </Button>
                          <Button variant="outline" size="sm" className="flex-1 hover:bg-primary/10 hover:text-primary hover:border-primary transition-colors">
                            <SettingsIcon className="h-4 w-4 mr-1" />
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
