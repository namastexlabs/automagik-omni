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
    // Agent Integration (Hive)
    agent_api_url: '',
    agent_api_key: '',
    default_agent: '',
    agent_id: '',
    agent_type: '',
    agent_timeout: 60,
    agent_stream_mode: false,
    enable_auto_split: true,
    automagik_instance_name: '',
    is_default: false,
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
        agent_id: instance.agent_id || '',
        agent_type: instance.agent_type || '',
        agent_timeout: instance.agent_timeout || 60,
        agent_stream_mode: instance.agent_stream_mode || false,
        enable_auto_split: instance.enable_auto_split ?? true,
        automagik_instance_name: instance.automagik_instance_name || '',
        is_default: instance.is_default || false,
        discord_client_id: instance.discord_client_id || '',
        discord_bot_token: '',
      });
      setError(null);
    }
  }, [open, instance]);

  const updateMutation = useMutation({
    mutationFn: (data: InstanceUpdateRequest) => api.instances.update(instance.name, data),
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
    if (formData.agent_id.trim()) {
      updateData.agent_id = formData.agent_id.trim();
    }
    if (formData.agent_type.trim()) {
      updateData.agent_type = formData.agent_type.trim();
    }
    updateData.agent_timeout = formData.agent_timeout;
    updateData.agent_stream_mode = formData.agent_stream_mode;
    updateData.enable_auto_split = formData.enable_auto_split;

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
            <DialogDescription>Configure agent integration for "{instance.name}"</DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Hive Agent Configuration Section */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-foreground">Hive Agent Configuration</h3>
              <p className="text-xs text-muted-foreground">Configure your Hive agent integration settings</p>

              <div className="space-y-3">
                <div className="space-y-2">
                  <Label htmlFor="agent_api_url" className="text-sm">
                    Hive API URL
                  </Label>
                  <Input
                    id="agent_api_url"
                    type="url"
                    value={formData.agent_api_url}
                    onChange={(e) => setFormData({ ...formData, agent_api_url: e.target.value })}
                    placeholder="https://api.hive.example.com"
                    disabled={isPending}
                  />
                  <p className="text-xs text-muted-foreground">The URL of your Hive agent API</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="agent_api_key" className="text-sm">
                    Hive API Key
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

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="agent_id" className="text-sm">
                      Agent ID
                    </Label>
                    <Input
                      id="agent_id"
                      value={formData.agent_id}
                      onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                      placeholder="agent-uuid"
                      disabled={isPending}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="agent_type" className="text-sm">
                      Agent Type
                    </Label>
                    <Input
                      id="agent_type"
                      value={formData.agent_type}
                      onChange={(e) => setFormData({ ...formData, agent_type: e.target.value })}
                      placeholder="e.g., assistant"
                      disabled={isPending}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="default_agent" className="text-sm">
                    Default Agent Name
                  </Label>
                  <Input
                    id="default_agent"
                    value={formData.default_agent}
                    onChange={(e) => setFormData({ ...formData, default_agent: e.target.value })}
                    placeholder="my-agent"
                    disabled={isPending}
                  />
                  <p className="text-xs text-muted-foreground">Agent name to use for incoming messages</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="agent_timeout" className="text-sm">
                    Response Timeout (seconds)
                  </Label>
                  <Input
                    id="agent_timeout"
                    type="number"
                    min={10}
                    max={300}
                    value={formData.agent_timeout}
                    onChange={(e) => setFormData({ ...formData, agent_timeout: parseInt(e.target.value) || 60 })}
                    disabled={isPending}
                  />
                  <p className="text-xs text-muted-foreground">Max time to wait for agent response (10-300s)</p>
                </div>

                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="space-y-0.5">
                    <Label htmlFor="agent_stream_mode" className="text-sm font-medium">
                      Stream Mode
                    </Label>
                    <p className="text-xs text-muted-foreground">Enable streaming responses from agent</p>
                  </div>
                  <Switch
                    id="agent_stream_mode"
                    checked={formData.agent_stream_mode}
                    onCheckedChange={(checked) => setFormData({ ...formData, agent_stream_mode: checked })}
                    disabled={isPending}
                  />
                </div>

                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="space-y-0.5">
                    <Label htmlFor="enable_auto_split" className="text-sm font-medium">
                      Auto-Split Messages
                    </Label>
                    <p className="text-xs text-muted-foreground">Split long responses into multiple messages</p>
                  </div>
                  <Switch
                    id="enable_auto_split"
                    checked={formData.enable_auto_split}
                    onCheckedChange={(checked) => setFormData({ ...formData, enable_auto_split: checked })}
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
                      <p className="text-xs text-muted-foreground">Only fill this if you want to change the token</p>
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
                <p className="text-xs text-muted-foreground">Use this connection for new conversations</p>
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
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
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
