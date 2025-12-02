import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/lib';
import type { InstanceConfig } from '@/lib';
import { DashboardLayout } from '@/components/DashboardLayout';
import { PageHeader } from '@/components/PageHeader';
import { ConnectionWizard, InstanceSettings } from '@/components/instances';
import { QRCodeDialog } from '@/components/QRCodeDialog';
import { InstanceCard } from '@/components/InstanceCard';
import { Plus, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';

export default function Instances() {
  const queryClient = useQueryClient();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [settingsInstance, setSettingsInstance] = useState<InstanceConfig | null>(null);
  const [qrInstance, setQrInstance] = useState<string | null>(null);

  const { data: instances, isLoading, error } = useQuery({
    queryKey: ['instances'],
    queryFn: () => api.instances.list({ limit: 100, include_status: true }),
    refetchInterval: 30000, // Refresh every 30s
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.instances.delete(name),
    onSuccess: (_, name) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Instance "${name}" deleted successfully`);
    },
    onError: (error: any, name) => {
      toast.error(`Failed to delete instance "${name}": ${error.message || 'Unknown error'}`);
    },
  });

  const handleDelete = (name: string) => {
    // Confirmation is now handled by InstanceCard's AlertDialog
    deleteMutation.mutate(name);
  };

  const handleSettings = (instance: InstanceConfig) => {
    setSettingsInstance(instance);
  };

  const handleShowQR = (instanceName: string) => {
    setQrInstance(instanceName);
  };

  return (
    <DashboardLayout>
      <div className="flex flex-col h-full">
        <PageHeader
          title="Connections"
          subtitle="Manage your messaging channel connections"
          actions={
            <Button
              className="gradient-primary elevation-md hover:elevation-lg transition-all hover-lift"
              onClick={() => setWizardOpen(true)}
              data-testid="add-connection"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Connection
            </Button>
          }
        />

        {/* Main Content */}
        <div className="flex-1 overflow-auto bg-background">
          <div className="p-8 space-y-6 animate-fade-in">
            {/* Error Alert */}
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Error loading instances: {error instanceof Error ? error.message : 'Unknown error'}
                </AlertDescription>
              </Alert>
            )}

            {/* Loading Skeletons */}
            {isLoading && (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {[...Array(6)].map((_, i) => (
                  <Card key={i} className="border-border elevation-md">
                    <CardHeader>
                      <Skeleton className="h-6 w-3/4 mb-2" />
                      <Skeleton className="h-4 w-1/2" />
                    </CardHeader>
                    <CardContent>
                      <Skeleton className="h-20 w-full" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Empty State */}
            {instances && instances.length === 0 && (
              <Card className="border-border elevation-md bg-gradient-to-br from-primary/5 to-primary/10">
                <CardContent className="pt-12 pb-12 text-center">
                  <div className="flex flex-col items-center space-y-4">
                    <div className="h-20 w-20 rounded-2xl gradient-primary flex items-center justify-center elevation-lg">
                      <Plus className="h-10 w-10 text-primary-foreground" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-foreground mb-2">No connections yet</p>
                      <p className="text-sm text-muted-foreground mb-6">
                        Connect your first WhatsApp or Discord account
                      </p>
                    </div>
                    <Button
                      className="gradient-primary elevation-md hover:elevation-lg hover-lift"
                      onClick={() => setWizardOpen(true)}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Add Connection
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Instance Cards */}
            {instances && instances.length > 0 && (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {instances.map((instance) => (
                  <InstanceCard
                    key={instance.id}
                    instance={instance}
                    onShowQR={handleShowQR}
                    onSettings={handleSettings}
                    onDelete={handleDelete}
                    isDeleting={deleteMutation.isPending}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Connection Wizard */}
      <ConnectionWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onSuccess={(instanceName, channelType) => {
          // Refresh instances list
          queryClient.invalidateQueries({ queryKey: ['instances'] });
        }}
      />

      {/* Instance Settings Dialog */}
      {settingsInstance && (
        <InstanceSettings
          open={settingsInstance !== null}
          onOpenChange={(open) => !open && setSettingsInstance(null)}
          instance={settingsInstance}
        />
      )}

      {/* QR Code Dialog (for reconnecting) */}
      {qrInstance && (
        <QRCodeDialog
          open={qrInstance !== null}
          onOpenChange={(open) => !open && setQrInstance(null)}
          instanceName={qrInstance}
        />
      )}
    </DashboardLayout>
  );
}
