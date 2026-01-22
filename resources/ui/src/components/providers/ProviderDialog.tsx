import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { api } from '@/lib';
import type { AgentProvider } from '@/lib';
import { AlertCircle, Loader2, Server } from 'lucide-react';

interface ProviderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider?: AgentProvider | null;
}

export function ProviderDialog({ open, onOpenChange, provider }: ProviderDialogProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const isEditing = !!provider;

  const [formData, setFormData] = useState({
    name: '',
    api_url: '',
    api_key: '',
    description: '',
    is_active: true,
  });

  // Initialize form with provider data when editing
  useEffect(() => {
    if (open) {
      if (provider) {
        setFormData({
          name: provider.name,
          api_url: provider.api_url,
          api_key: '', // Don't populate existing key for security
          description: provider.description || '',
          is_active: provider.is_active,
        });
      } else {
        setFormData({
          name: '',
          api_url: '',
          api_key: '',
          description: '',
          is_active: true,
        });
      }
      setError(null);
    }
  }, [open, provider]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: typeof formData) =>
      api.providers.create({
        name: data.name,
        api_url: data.api_url,
        api_key: data.api_key,
        description: data.description || undefined,
        is_active: data.is_active,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      toast.success('Provider created successfully');
      onOpenChange(false);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to create provider');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: typeof formData) =>
      api.providers.update(provider!.id, {
        name: data.name !== provider!.name ? data.name : undefined,
        api_url: data.api_url !== provider!.api_url ? data.api_url : undefined,
        api_key: data.api_key.trim() ? data.api_key : undefined, // Only update if provided
        description: data.description !== (provider!.description || '') ? data.description : undefined,
        is_active: data.is_active !== provider!.is_active ? data.is_active : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      toast.success('Provider updated successfully');
      onOpenChange(false);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to update provider');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!formData.name.trim()) {
      setError('Provider name is required');
      return;
    }
    if (!formData.api_url.trim()) {
      setError('API URL is required');
      return;
    }
    if (!isEditing && !formData.api_key.trim()) {
      setError('API key is required');
      return;
    }

    if (isEditing) {
      updateMutation.mutate(formData);
    } else {
      createMutation.mutate(formData);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" />
              {isEditing ? 'Edit Provider' : 'Add Agent Provider'}
            </DialogTitle>
            <DialogDescription>
              {isEditing
                ? 'Update the provider configuration'
                : 'Configure a new agent provider to share API credentials across instances'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="name" className="text-sm">
                Provider Name *
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Production Agno"
                disabled={isPending}
              />
              <p className="text-xs text-muted-foreground">A unique name to identify this provider</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="api_url" className="text-sm">
                API URL *
              </Label>
              <Input
                id="api_url"
                type="url"
                value={formData.api_url}
                onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                placeholder="https://api.agno.example.com"
                disabled={isPending}
              />
              <p className="text-xs text-muted-foreground">The base URL of the agent API</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="api_key" className="text-sm">
                API Key {!isEditing && '*'}
              </Label>
              <Input
                id="api_key"
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                placeholder={isEditing ? 'Leave empty to keep current' : 'Enter API key'}
                disabled={isPending}
              />
              {isEditing && <p className="text-xs text-muted-foreground">Leave empty to keep the current API key</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description" className="text-sm">
                Description
              </Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Optional description for this provider"
                rows={2}
                disabled={isPending}
              />
            </div>

            <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
              <div className="space-y-0.5">
                <Label htmlFor="is_active" className="text-sm font-medium">
                  Active
                </Label>
                <p className="text-xs text-muted-foreground">Enable this provider for use by instances</p>
              </div>
              <Switch
                id="is_active"
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                disabled={isPending}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {isEditing ? 'Saving...' : 'Creating...'}
                </>
              ) : isEditing ? (
                'Save Changes'
              ) : (
                'Create Provider'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
