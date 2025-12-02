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
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib';
import type { InstanceConfig, InstanceUpdateRequest } from '@/lib';
import { AlertCircle, Loader2, Settings } from 'lucide-react';

interface InstanceSettingsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instance: InstanceConfig;
}

export function InstanceSettings({ open, onOpenChange, instance }: InstanceSettingsProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    agent_api_url: '',
    agent_api_key: '',
    default_agent: '',
    automagik_instance_name: '',
    is_default: false,
    // WhatsApp specific
    phone_number: '',
    // Discord specific
    discord_client_id: '',
    discord_bot_token: '',
  });

  // Initialize form with instance data
  useEffect(() => {
    if (open && instance) {
      setFormData({
        agent_api_url: instance.agent_api_url || '',
        agent_api_key: instance.agent_api_key || '',
        default_agent: instance.default_agent || '',
        automagik_instance_name: instance.automagik_instance_name || '',
        is_default: instance.is_default || false,
        phone_number: '',
        discord_client_id: instance.discord_client_id || '',
        discord_bot_token: '',
      });
      setError(null);
    }
  }, [open, instance]);

  const updateMutation = useMutation({
    mutationFn: (data: InstanceUpdateRequest) =>
      api.instances.update(instance.name, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Settings for "${instance.name}" updated`);
      onOpenChange(false);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to update settings');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const updateData: InstanceUpdateRequest = {
      is_default: formData.is_default,
    };

    // Only include non-empty optional fields
    if (formData.agent_api_url.trim()) {
      updateData.agent_api_url = formData.agent_api_url.trim();
    }
    if (formData.agent_api_key.trim()) {
      updateData.agent_api_key = formData.agent_api_key.trim();
    }
    if (formData.default_agent.trim()) {
      updateData.default_agent = formData.default_agent.trim();
    }

    // Discord-specific
    if (instance.channel_type === 'discord') {
      if (formData.discord_client_id.trim()) {
        updateData.discord_client_id = formData.discord_client_id.trim();
      }
      if (formData.discord_bot_token.trim()) {
        updateData.discord_bot_token = formData.discord_bot_token.trim();
      }
    }

    updateMutation.mutate(updateData);
  };

  const isPending = updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5 text-primary" />
              Connection Settings
            </DialogTitle>
            <DialogDescription>
              Configure agent integration for "{instance.name}"
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Agent Configuration Section */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-foreground">Agent Integration</h3>

              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="agent_api_url" className="text-sm">
                    Agent API URL
                  </Label>
                  <Input
                    id="agent_api_url"
                    type="url"
                    value={formData.agent_api_url}
                    onChange={(e) => setFormData({ ...formData, agent_api_url: e.target.value })}
                    placeholder="https://your-agent-api.com"
                    disabled={isPending}
                  />
                  <p className="text-xs text-muted-foreground">
                    The URL of your Automagik agent API
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="agent_api_key" className="text-sm">
                    Agent API Key
                  </Label>
                  <Input
                    id="agent_api_key"
                    type="password"
                    value={formData.agent_api_key}
                    onChange={(e) => setFormData({ ...formData, agent_api_key: e.target.value })}
                    placeholder={instance.agent_api_key ? '••••••••' : 'Enter API key'}
                    disabled={isPending}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="default_agent" className="text-sm">
                    Default Agent
                  </Label>
                  <Input
                    id="default_agent"
                    value={formData.default_agent}
                    onChange={(e) => setFormData({ ...formData, default_agent: e.target.value })}
                    placeholder="agent-name"
                    disabled={isPending}
                  />
                  <p className="text-xs text-muted-foreground">
                    Agent to use for incoming messages
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="automagik_instance_name" className="text-sm">
                    Automagik Instance
                  </Label>
                  <Input
                    id="automagik_instance_name"
                    value={formData.automagik_instance_name}
                    onChange={(e) => setFormData({ ...formData, automagik_instance_name: e.target.value })}
                    placeholder="my-automagik-instance"
                    disabled={isPending}
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Discord-specific settings */}
            {instance.channel_type === 'discord' && (
              <>
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-foreground">Discord Settings</h3>

                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="discord_client_id" className="text-sm">
                        Client ID
                      </Label>
                      <Input
                        id="discord_client_id"
                        value={formData.discord_client_id}
                        onChange={(e) => setFormData({ ...formData, discord_client_id: e.target.value })}
                        placeholder="123456789012345678"
                        disabled={isPending}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="discord_bot_token" className="text-sm">
                        Bot Token
                      </Label>
                      <Input
                        id="discord_bot_token"
                        type="password"
                        value={formData.discord_bot_token}
                        onChange={(e) => setFormData({ ...formData, discord_bot_token: e.target.value })}
                        placeholder="Leave empty to keep current token"
                        disabled={isPending}
                      />
                      <p className="text-xs text-muted-foreground">
                        Only fill this if you want to change the token
                      </p>
                    </div>
                  </div>
                </div>

                <Separator />
              </>
            )}

            {/* Default Switch */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="is_default" className="text-sm font-medium">
                  Default Connection
                </Label>
                <p className="text-xs text-muted-foreground">
                  Use this connection for new conversations
                </p>
              </div>
              <Switch
                id="is_default"
                checked={formData.is_default}
                onCheckedChange={(checked) => setFormData({ ...formData, is_default: checked })}
                disabled={isPending}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Settings'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
