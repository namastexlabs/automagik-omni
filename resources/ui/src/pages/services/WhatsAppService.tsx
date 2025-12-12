import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { WhatsAppConnector } from '@/components/instances/WhatsAppConnector';
import { EvolutionStartupModal } from '@/components/EvolutionStartupModal';
import { api } from '@/lib';
import type { InstanceConfig } from '@/lib';
import {
  MessageCircle,
  ArrowLeft,
  Plus,
  Play,
  Square,
  RotateCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Settings,
  Trash2,
} from 'lucide-react';

type ServiceStatus = 'up' | 'down' | 'degraded' | 'unknown';

function getStatusBadge(status: ServiceStatus) {
  switch (status) {
    case 'up':
      return (
        <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          Running
        </Badge>
      );
    case 'down':
      return (
        <Badge variant="destructive" className="bg-red-500/10 text-red-500 border-red-500/20">
          <XCircle className="h-3 w-3 mr-1" />
          Stopped
        </Badge>
      );
    case 'degraded':
      return (
        <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
          <AlertCircle className="h-3 w-3 mr-1" />
          Degraded
        </Badge>
      );
    default:
      return (
        <Badge variant="secondary">
          <AlertCircle className="h-3 w-3 mr-1" />
          Unknown
        </Badge>
      );
  }
}

export default function WhatsAppService() {
  const queryClient = useQueryClient();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardInstanceName, setWizardInstanceName] = useState('');
  const [showStartupModal, setShowStartupModal] = useState(false);

  // Fetch health status
  const { data: healthData, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 5000,
  });

  // Fetch WhatsApp instances
  const { data: instances, isLoading: instancesLoading } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_status: true }),
    refetchInterval: 10000,
  });

  const evolutionStatus: ServiceStatus = healthData?.services?.evolution?.status || 'unknown';
  const whatsappInstances = instances?.filter((i) => i.channel_type === 'whatsapp') || [];
  const isLoading = healthLoading || instancesLoading;

  // Start service mutation
  const startMutation = useMutation({
    mutationFn: () => api.gateway.startChannel('evolution'),
    onSuccess: () => {
      toast.success('WhatsApp service started');
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to start service: ${err.message}`);
    },
  });

  // Stop service mutation
  const stopMutation = useMutation({
    mutationFn: () => api.gateway.stopChannel('evolution'),
    onSuccess: () => {
      toast.success('WhatsApp service stopped');
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to stop service: ${err.message}`);
    },
  });

  // Restart service mutation
  const restartMutation = useMutation({
    mutationFn: () => api.gateway.restartChannel('evolution'),
    onSuccess: () => {
      toast.success('WhatsApp service restarted');
      queryClient.invalidateQueries({ queryKey: ['health'] });
    },
    onError: (err: Error) => {
      toast.error(`Failed to restart service: ${err.message}`);
    },
  });

  // Delete instance mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.instances.delete(name),
    onSuccess: (_: void, name) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Instance "${name}" deleted`);
    },
    onError: (err: Error, name) => {
      toast.error(`Failed to delete "${name}": ${err.message}`);
    },
  });

  const isServiceBusy = startMutation.isPending || stopMutation.isPending || restartMutation.isPending;

  const handleStartService = async () => {
    if (evolutionStatus === 'down' || evolutionStatus === 'unknown') {
      setShowStartupModal(true);
      try {
        await api.gateway.startChannel('evolution');
      } catch {
        // Error will be shown in modal via logs
      }
    }
  };

  const handleAddInstance = () => {
    // Generate a default instance name
    const baseName = 'whatsapp';
    const existingNames = whatsappInstances.map((i) => i.name);
    let counter = 1;
    let newName = baseName;
    while (existingNames.includes(newName)) {
      newName = `${baseName}-${counter}`;
      counter++;
    }
    setWizardInstanceName(newName);
    setWizardOpen(true);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="WhatsApp Service"
          subtitle="Manage your WhatsApp connections via Evolution API"
          actions={
            <Button variant="outline" asChild>
              <Link to="/services">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Services
              </Link>
            </Button>
          }
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {/* Service Status Card */}
            <Card className="border-border elevation-md">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-xl bg-[#25D366] flex items-center justify-center">
                      <MessageCircle className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <CardTitle>Evolution API Service</CardTitle>
                      <CardDescription>WhatsApp Web integration service</CardDescription>
                    </div>
                  </div>
                  {isLoading ? <Skeleton className="h-6 w-20" /> : getStatusBadge(evolutionStatus)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-3">
                  {evolutionStatus === 'down' || evolutionStatus === 'unknown' ? (
                    <Button
                      onClick={handleStartService}
                      disabled={isServiceBusy}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      {startMutation.isPending ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Play className="h-4 w-4 mr-2" />
                      )}
                      Start Service
                    </Button>
                  ) : (
                    <>
                      <Button variant="destructive" onClick={() => stopMutation.mutate()} disabled={isServiceBusy}>
                        {stopMutation.isPending ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <Square className="h-4 w-4 mr-2" />
                        )}
                        Stop
                      </Button>
                      <Button variant="outline" onClick={() => restartMutation.mutate()} disabled={isServiceBusy}>
                        {restartMutation.isPending ? (
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                          <RotateCw className="h-4 w-4 mr-2" />
                        )}
                        Restart
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Instances Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">WhatsApp Instances</h2>
                <Button onClick={handleAddInstance} disabled={evolutionStatus !== 'up'}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Instance
                </Button>
              </div>

              {evolutionStatus !== 'up' && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>Start the Evolution API service to manage WhatsApp instances.</AlertDescription>
                </Alert>
              )}

              {instancesLoading ? (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {[1, 2, 3].map((i) => (
                    <Card key={i} className="border-border">
                      <CardHeader>
                        <Skeleton className="h-5 w-32 mb-2" />
                        <Skeleton className="h-4 w-24" />
                      </CardHeader>
                      <CardContent>
                        <Skeleton className="h-8 w-full" />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : whatsappInstances.length === 0 ? (
                <Card className="border-border border-dashed">
                  <CardContent className="py-12 text-center">
                    <div className="flex flex-col items-center space-y-4">
                      <div className="h-16 w-16 rounded-2xl bg-muted flex items-center justify-center">
                        <MessageCircle className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium text-foreground">No WhatsApp instances</p>
                        <p className="text-sm text-muted-foreground mt-1">Add your first WhatsApp connection</p>
                      </div>
                      <Button onClick={handleAddInstance} disabled={evolutionStatus !== 'up'}>
                        <Plus className="h-4 w-4 mr-2" />
                        Add Instance
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {whatsappInstances.map((instance) => (
                    <InstanceCard
                      key={instance.id}
                      instance={instance}
                      onDelete={() => deleteMutation.mutate(instance.name)}
                      isDeleting={deleteMutation.isPending}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Instance Dialog */}
      <Dialog open={wizardOpen} onOpenChange={setWizardOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add WhatsApp Instance</DialogTitle>
          </DialogHeader>
          <WhatsAppConnector
            instanceName={wizardInstanceName}
            onBack={() => setWizardOpen(false)}
            onSuccess={() => {
              setWizardOpen(false);
              queryClient.invalidateQueries({ queryKey: ['instances'] });
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Evolution Startup Modal */}
      <EvolutionStartupModal
        open={showStartupModal}
        onOpenChange={setShowStartupModal}
        onSuccess={() => {
          setShowStartupModal(false);
          queryClient.invalidateQueries({ queryKey: ['health'] });
          toast.success('WhatsApp service started successfully');
        }}
        onRetry={() => {
          // Retry logic handled by modal
        }}
      />
    </DashboardLayout>
  );
}

// Instance card component
function InstanceCard({
  instance,
  onDelete,
  isDeleting,
}: {
  instance: InstanceConfig;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const isConnected = instance.whatsapp_status?.connected || false;

  return (
    <Card className="border-border hover:elevation-md transition-all">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{instance.name}</CardTitle>
          {isConnected ? (
            <Badge className="bg-green-500/10 text-green-500 border-green-500/20">
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Connected
            </Badge>
          ) : (
            <Badge variant="secondary">
              <XCircle className="h-3 w-3 mr-1" />
              Disconnected
            </Badge>
          )}
        </div>
        {instance.whatsapp_status?.phone_number && (
          <CardDescription>{instance.whatsapp_status.phone_number}</CardDescription>
        )}
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild className="flex-1">
            <Link to={`/instances`}>
              <Settings className="h-4 w-4 mr-1" />
              Settings
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onDelete}
            disabled={isDeleting}
            className="text-destructive hover:text-destructive"
          >
            {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
