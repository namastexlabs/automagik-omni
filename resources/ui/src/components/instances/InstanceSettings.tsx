import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { api } from '@/lib';
import type { InstanceConfig, InstanceUpdateRequest } from '@/lib';
import { AlertCircle, Loader2, Settings, Server, RefreshCw } from 'lucide-react';

interface InstanceSettingsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instance: InstanceConfig;
}

type ConfigMode = 'provider' | 'manual';

export function InstanceSettings({ open, onOpenChange, instance }: InstanceSettingsProps) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [configMode, setConfigMode] = useState<ConfigMode>('manual');
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [agents, setAgents] = useState<Array<{ id: string; name: string | null }>>([]);
  const [teams, setTeams] = useState<Array<{ id: string; name: string | null }>>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);

  const [formData, setFormData] = useState({
    // Agent Integration
    agent_api_url: '',
    agent_api_key: '',
    agent_id: '',
    agent_type: 'agent' as 'agent' | 'team',
    agent_timeout: 60,
    agent_stream_mode: false,
    enable_auto_split: true,
    is_default: false,
    // Discord specific
    discord_client_id: '',
    discord_bot_token: '',
  });

  // Fetch providers
  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: () => api.providers.list(),
    enabled: open,
  });

  // Get selected provider
  const selectedProvider = providers?.find((p) => p.id === selectedProviderId);

  // Initialize form with instance data
  useEffect(() => {
    if (open && instance) {
      const hasProvider = instance.agent_provider_id != null;
      setConfigMode(hasProvider ? 'provider' : 'manual');
      setSelectedProviderId(instance.agent_provider_id || null);

      setFormData({
        agent_api_url: instance.agent_api_url || '',
        agent_api_key: instance.agent_api_key || '',
        agent_id: instance.agent_id || '',
        agent_type: (instance.agent_type as 'agent' | 'team') || 'agent',
        agent_timeout: instance.agent_timeout || 60,
        agent_stream_mode: instance.agent_stream_mode || false,
        enable_auto_split: instance.enable_auto_split ?? true,
        is_default: instance.is_default || false,
        discord_client_id: instance.discord_client_id || '',
        discord_bot_token: '',
      });
      setError(null);
      setAgents([]);
      setTeams([]);
    }
  }, [open, instance]);

  // Fetch agents/teams when provider changes
  useEffect(() => {
    if (selectedProviderId && configMode === 'provider') {
      fetchAgentsAndTeams(selectedProviderId);
    }
  }, [selectedProviderId, configMode]);

  const fetchAgentsAndTeams = async (providerId: number) => {
    setLoadingAgents(true);
    try {
      const [agentsData, teamsData] = await Promise.all([
        api.providers.fetchAgents(providerId),
        api.providers.fetchTeams(providerId),
      ]);
      setAgents(agentsData);
      setTeams(teamsData);
    } catch (err) {
      console.error('Failed to fetch agents/teams:', err);
      setAgents([]);
      setTeams([]);
    } finally {
      setLoadingAgents(false);
    }
  };

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
      agent_instance_type: 'hive',
    };

    // Provider vs Manual configuration
    if (configMode === 'provider' && selectedProviderId) {
      updateData.agent_provider_id = selectedProviderId;
      // Clear manual credentials when using provider
      updateData.agent_api_url = '';
      updateData.agent_api_key = '';
    } else {
      // Manual configuration
      updateData.agent_provider_id = null;
      if (formData.agent_api_url.trim()) {
        updateData.agent_api_url = formData.agent_api_url.trim();
      }
      if (formData.agent_api_key.trim()) {
        updateData.agent_api_key = formData.agent_api_key.trim();
      }
    }

    // Common fields
    if (formData.agent_id.trim()) {
      updateData.agent_id = formData.agent_id.trim();
    }
    updateData.agent_type = formData.agent_type;
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

  const handleConfigModeChange = (mode: ConfigMode) => {
    setConfigMode(mode);
    if (mode === 'manual') {
      setSelectedProviderId(null);
      setAgents([]);
      setTeams([]);
    }
  };

  const handleProviderChange = (value: string) => {
    const providerId = parseInt(value, 10);
    setSelectedProviderId(providerId);
    // Reset agent selection when provider changes
    setFormData((prev) => ({ ...prev, agent_id: '', agent_type: 'agent' }));
  };

  const isPending = updateMutation.isPending;

  // Combine agents and teams for the dropdown
  const agentOptions = [
    ...agents.map((a) => ({ id: a.id, name: a.name || a.id, type: 'agent' as const })),
    ...teams.map((t) => ({ id: t.id, name: t.name || t.id, type: 'team' as const })),
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
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

            {/* Configuration Mode Selection */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Agent API Configuration</Label>
              <Select
                value={configMode}
                onValueChange={(value) => handleConfigModeChange(value as ConfigMode)}
                disabled={isPending}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="provider">
                    <div className="flex items-center gap-2">
                      <Server className="h-4 w-4" />
                      Use Saved Provider
                    </div>
                  </SelectItem>
                  <SelectItem value="manual">Manual Configuration</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Provider Selection */}
            {configMode === 'provider' && (
              <div className="space-y-4 p-4 bg-muted/50 rounded-lg border">
                <div className="space-y-2">
                  <Label htmlFor="provider" className="text-sm">
                    Select Provider
                  </Label>
                  <Select
                    value={selectedProviderId?.toString() || ''}
                    onValueChange={handleProviderChange}
                    disabled={isPending}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Choose a provider..." />
                    </SelectTrigger>
                    <SelectContent>
                      {providers?.map((provider) => (
                        <SelectItem key={provider.id} value={provider.id.toString()}>
                          {provider.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {selectedProvider && (
                  <>
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">API URL (from provider)</Label>
                      <code className="block text-xs bg-background p-2 rounded border">{selectedProvider.api_url}</code>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="agent_select" className="text-sm">
                        Agent / Team
                      </Label>
                      <div className="flex gap-2">
                        <Select
                          value={`${formData.agent_type}:${formData.agent_id}`}
                          onValueChange={(value) => {
                            const [type, id] = value.split(':');
                            setFormData((prev) => ({
                              ...prev,
                              agent_type: type as 'agent' | 'team',
                              agent_id: id,
                            }));
                          }}
                          disabled={isPending || loadingAgents}
                        >
                          <SelectTrigger className="flex-1">
                            <SelectValue placeholder={loadingAgents ? 'Loading...' : 'Select agent or team...'} />
                          </SelectTrigger>
                          <SelectContent>
                            {agentOptions.map((option) => (
                              <SelectItem key={`${option.type}:${option.id}`} value={`${option.type}:${option.id}`}>
                                <span className="capitalize">[{option.type}]</span> {option.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => selectedProviderId && fetchAgentsAndTeams(selectedProviderId)}
                          disabled={loadingAgents || !selectedProviderId}
                        >
                          <RefreshCw className={`h-4 w-4 ${loadingAgents ? 'animate-spin' : ''}`} />
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {agentOptions.length > 0
                          ? `${agents.length} agents, ${teams.length} teams available`
                          : loadingAgents
                            ? 'Fetching...'
                            : 'No agents/teams found'}
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Manual Configuration */}
            {configMode === 'manual' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-foreground">Agent Configuration</h3>
                <p className="text-xs text-muted-foreground">Configure agent integration manually</p>

                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label htmlFor="agent_api_url" className="text-sm">
                      API URL
                    </Label>
                    <Input
                      id="agent_api_url"
                      type="url"
                      value={formData.agent_api_url}
                      onChange={(e) => setFormData({ ...formData, agent_api_url: e.target.value })}
                      placeholder="https://api.agno.example.com"
                      disabled={isPending}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="agent_api_key" className="text-sm">
                      API Key
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
                      Type
                    </Label>
                    <Select
                      value={formData.agent_type}
                      onValueChange={(value) => setFormData({ ...formData, agent_type: value as 'agent' | 'team' })}
                      disabled={isPending}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="agent">Agent</SelectItem>
                        <SelectItem value="team">Team</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}

            <Separator />

            {/* Common Agent Settings */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-foreground">Agent Behavior</h3>

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

            {/* Discord-specific settings */}
            {instance.channel_type === 'discord' && (
              <>
                <Separator />
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
              </>
            )}

            <Separator />

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
