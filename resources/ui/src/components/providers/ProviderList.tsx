import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
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
import { api, formatDateTime } from '@/lib';
import type { AgentProvider } from '@/lib';
import { ProviderDialog } from './ProviderDialog';
import { Server, Plus, Pencil, Trash2, RefreshCw, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';

export function ProviderList() {
  const queryClient = useQueryClient();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingProvider, setEditingProvider] = useState<AgentProvider | null>(null);
  const [deletingProvider, setDeletingProvider] = useState<AgentProvider | null>(null);
  const [checkingHealthId, setCheckingHealthId] = useState<number | null>(null);

  // Fetch providers
  const { data: providers, isLoading } = useQuery({
    queryKey: ['providers'],
    queryFn: () => api.providers.list(true), // Include inactive
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.providers.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      toast.success('Provider deleted successfully');
      setDeletingProvider(null);
    },
    onError: (err: Error) => {
      toast.error(`Failed to delete provider: ${err.message}`);
    },
  });

  // Health check mutation
  const healthCheckMutation = useMutation({
    mutationFn: (id: number) => api.providers.checkHealth(id),
    onSuccess: (data, id) => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      if (data.status === 'healthy') {
        toast.success('Provider is healthy');
      } else {
        toast.warning(`Provider health check: ${data.status}${data.message ? ` - ${data.message}` : ''}`);
      }
      setCheckingHealthId(null);
    },
    onError: (err: Error) => {
      toast.error(`Health check failed: ${err.message}`);
      setCheckingHealthId(null);
    },
  });

  const handleCheckHealth = (provider: AgentProvider) => {
    setCheckingHealthId(provider.id);
    healthCheckMutation.mutate(provider.id);
  };

  const getHealthBadge = (status: string | null) => {
    switch (status) {
      case 'healthy':
        return (
          <Badge variant="default" className="bg-green-500 hover:bg-green-600">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Healthy
          </Badge>
        );
      case 'unhealthy':
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Unhealthy
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
  };

  if (isLoading) {
    return (
      <Card className="border-border elevation-md">
        <CardHeader>
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-60" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className="border-border elevation-md">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5 text-primary" />
                Agent Providers
              </CardTitle>
              <CardDescription>Reusable API configurations that can be shared across instances</CardDescription>
            </div>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Provider
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {providers && providers.length > 0 ? (
            <div className="space-y-3">
              {providers.map((provider) => (
                <div
                  key={provider.id}
                  className={`p-4 bg-muted rounded-lg border border-border space-y-2 ${
                    !provider.is_active ? 'opacity-60' : ''
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-semibold">{provider.name}</span>
                        {!provider.is_active && (
                          <Badge variant="outline" className="text-xs">
                            Inactive
                          </Badge>
                        )}
                        {getHealthBadge(provider.last_health_status)}
                      </div>
                      {provider.description && (
                        <p className="text-xs text-muted-foreground mb-2">{provider.description}</p>
                      )}
                      <code className="text-xs text-muted-foreground font-mono">{provider.api_url}</code>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span>Created: {formatDateTime(provider.created_at)}</span>
                        {provider.last_health_check && (
                          <span>Last check: {formatDateTime(provider.last_health_check)}</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCheckHealth(provider)}
                        disabled={checkingHealthId === provider.id}
                      >
                        {checkingHealthId === provider.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4" />
                        )}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditingProvider(provider)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setDeletingProvider(provider)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Server className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-sm">No agent providers configured</p>
              <p className="text-xs mt-1">Add a provider to share API credentials across instances</p>
            </div>
          )}

          <Separator className="my-4" />
          <p className="text-xs text-muted-foreground">
            Agent providers allow you to configure API credentials once and reuse them across multiple instances. When
            an instance is linked to a provider, it will use the provider's credentials for agent communication.
          </p>
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <ProviderDialog
        open={showCreateDialog || !!editingProvider}
        onOpenChange={(open) => {
          if (!open) {
            setShowCreateDialog(false);
            setEditingProvider(null);
          }
        }}
        provider={editingProvider}
      />

      {/* Delete Confirmation */}
      <AlertDialog open={!!deletingProvider} onOpenChange={(open) => !open && setDeletingProvider(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Provider</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deletingProvider?.name}"? Instances using this provider will need to be
              reconfigured.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deletingProvider && deleteMutation.mutate(deletingProvider.id)}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
