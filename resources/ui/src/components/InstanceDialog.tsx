import { useState, useEffect, useMemo } from 'react';
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { api } from '@/lib';
import type { InstanceConfig, InstanceCreateRequest, InstanceUpdateRequest, ProviderAgent, ProviderTeam } from '@/lib';
import { AlertCircle, Loader2, Server, Settings2, Bot, Users } from 'lucide-react';

// Available channels (only implemented ones)
const CHANNELS = {
  whatsapp: 'WhatsApp Web',
  discord: 'Discord',
} as const;

interface InstanceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  instance?: InstanceConfig | null;
  onInstanceCreated?: (instanceName: string, channelType: string) => void;
}

// Combined agent/team item for dropdown
interface AgentOrTeam {
  id: string;
  name: string;
  description?: string | null;
  type: 'agent' | 'team';
}

// Normalize instance name: remove spaces, convert to lowercase, replace with hyphens
function normalizeInstanceName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-_]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

export function InstanceDialog({ open, onOpenChange, instance, onInstanceCreated }: InstanceDialogProps) {
  const queryClient = useQueryClient();
  const isEditing = !!instance;

  const [formData, setFormData] = useState({
    name: '',
    channel_type: 'whatsapp',
    agent_provider_id: null as number | null,
    agent_api_url: '',
    agent_api_key: '',
    agent_id: '',
    is_default: false,
    phone_number: '',
    discord_bot_token: '',
    discord_client_id: '',
  });

  const [error, setError] = useState<string | null>(null);
  const [nameWarning, setNameWarning] = useState<string | null>(null);
  const [configMode, setConfigMode] = useState<'provider' | 'manual'>('provider');

  // Fetch available providers
  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: () => api.providers.list(false),
    enabled: open,
  });

  // Fetch agents from selected provider
  const { data: providerAgents, isLoading: isLoadingAgents } = useQuery({
    queryKey: ['provider-agents', formData.agent_provider_id],
    queryFn: () => api.providers.fetchAgents(formData.agent_provider_id!),
    enabled: !!formData.agent_provider_id && configMode === 'provider',
  });

  // Fetch teams from selected provider
  const { data: providerTeams, isLoading: isLoadingTeams } = useQuery({
    queryKey: ['provider-teams', formData.agent_provider_id],
    queryFn: () => api.providers.fetchTeams(formData.agent_provider_id!),
    enabled: !!formData.agent_provider_id && configMode === 'provider',
  });

  // Combine agents and teams into a single list
  const agentsAndTeams = useMemo<AgentOrTeam[]>(() => {
    const items: AgentOrTeam[] = [];

    if (providerAgents) {
      providerAgents.forEach((agent: ProviderAgent) => {
        items.push({
          id: `agent:${agent.id}`,
          name: agent.name || agent.id,
          description: agent.description,
          type: 'agent',
        });
      });
    }

    if (providerTeams) {
      providerTeams.forEach((team: ProviderTeam) => {
        items.push({
          id: `team:${team.id}`,
          name: team.name || team.id,
          description: team.description,
          type: 'team',
        });
      });
    }

    return items;
  }, [providerAgents, providerTeams]);

  // Get selected item for description display
  const selectedItem = useMemo(() => {
    if (!formData.agent_id) return null;
    return agentsAndTeams.find((item) => item.id === formData.agent_id);
  }, [formData.agent_id, agentsAndTeams]);

  const isLoadingItems = isLoadingAgents || isLoadingTeams;

  // Reset form when dialog opens/closes or instance changes
  useEffect(() => {
    if (open) {
      if (instance) {
        const hasProvider = !!instance.agent_provider_id;
        setConfigMode(hasProvider ? 'provider' : 'manual');
        setFormData({
          name: instance.name,
          channel_type: instance.channel_type,
          agent_provider_id: instance.agent_provider_id || null,
          agent_api_url: instance.agent_api_url || '',
          agent_api_key: instance.agent_api_key || '',
          agent_id: instance.agent_id || '',
          is_default: instance.is_default,
          phone_number: instance.phone_number || '',
          discord_bot_token: '',
          discord_client_id: instance.discord_client_id || '',
        });
      } else {
        setConfigMode('provider');
        setFormData({
          name: '',
          channel_type: 'whatsapp',
          agent_provider_id: null,
          agent_api_url: '',
          agent_api_key: '',
          agent_id: '',
          is_default: false,
          phone_number: '',
          discord_bot_token: '',
          discord_client_id: '',
        });
      }
      setError(null);
      setNameWarning(null);
    }
  }, [open, instance]);

  // When provider changes, update the agent_api_url
  useEffect(() => {
    if (configMode === 'provider' && formData.agent_provider_id && providers) {
      const provider = providers.find((p) => p.id === formData.agent_provider_id);
      if (provider) {
        setFormData((prev) => ({
          ...prev,
          agent_api_url: provider.api_url,
        }));
      }
    }
  }, [formData.agent_provider_id, providers, configMode]);

  const createMutation = useMutation({
    mutationFn: (data: InstanceCreateRequest) => api.instances.create(data),
    onSuccess: (createdInstance) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Instance "${createdInstance.name}" created successfully`);
      onOpenChange(false);
      if (onInstanceCreated && createdInstance.channel_type === 'whatsapp') {
        onInstanceCreated(createdInstance.name, createdInstance.channel_type);
      }
    },
    onError: (error: Error) => {
      setError(error.message);
      toast.error(`Failed to create instance: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: InstanceUpdateRequest }) => api.instances.update(name, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['instances'] });
      toast.success(`Instance "${variables.name}" updated successfully`);
      onOpenChange(false);
    },
    onError: (error: Error, variables) => {
      setError(error.message);
      toast.error(`Failed to update instance "${variables.name}": ${error.message}`);
    },
  });

  const handleNameChange = (value: string) => {
    const normalized = normalizeInstanceName(value);
    setFormData({ ...formData, name: value });

    if (value !== normalized && value.length > 0) {
      setNameWarning(`Will be saved as: "${normalized}"`);
    } else {
      setNameWarning(null);
    }
  };

  const handleConfigModeChange = (mode: 'provider' | 'manual') => {
    setConfigMode(mode);
    if (mode === 'manual') {
      setFormData((prev) => ({
        ...prev,
        agent_provider_id: null,
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        agent_api_url: '',
        agent_api_key: '',
      }));
    }
  };

  const handleProviderChange = (providerId: string) => {
    const id = providerId === 'none' ? null : parseInt(providerId, 10);
    setFormData((prev) => ({
      ...prev,
      agent_provider_id: id,
      agent_id: '',
    }));
  };

  // Parse agent_id to extract actual ID (remove type prefix)
  const getActualAgentId = (compositeId: string): string => {
    if (compositeId.startsWith('agent:') || compositeId.startsWith('team:')) {
      return compositeId.split(':')[1];
    }
    return compositeId;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const normalizedName = normalizeInstanceName(formData.name);

    if (!normalizedName) {
      setError('Instance name is required and must contain valid characters');
      return;
    }

    if (configMode === 'provider') {
      if (!formData.agent_provider_id) {
        setError('Please select an Agent Provider');
        return;
      }
    } else {
      if (!formData.agent_api_url) {
        setError('Agent API URL is required');
        return;
      }
      if (!formData.agent_api_key) {
        setError('Agent API Key is required');
        return;
      }
    }

    // Extract actual agent ID from composite ID
    const actualAgentId = formData.agent_id ? getActualAgentId(formData.agent_id) : undefined;

    if (isEditing) {
      const updateData: InstanceUpdateRequest = {
        is_default: formData.is_default,
        agent_provider_id: configMode === 'provider' ? formData.agent_provider_id : null,
        agent_api_url: configMode === 'manual' ? formData.agent_api_url : undefined,
        agent_api_key: configMode === 'manual' ? formData.agent_api_key : undefined,
        agent_id: actualAgentId,
        agent_instance_type: 'hive',
      };

      if (formData.channel_type === 'whatsapp') {
        updateData.phone_number = formData.phone_number || null;
      } else if (formData.channel_type === 'discord') {
        if (formData.discord_bot_token) {
          updateData.discord_bot_token = formData.discord_bot_token;
        }
        updateData.discord_client_id = formData.discord_client_id || null;
      }

      updateMutation.mutate({ name: instance.name, data: updateData });
    } else {
      const createData: InstanceCreateRequest = {
        name: normalizedName,
        channel_type: formData.channel_type,
        agent_provider_id: configMode === 'provider' ? formData.agent_provider_id : undefined,
        agent_api_url: configMode === 'manual' ? formData.agent_api_url : undefined,
        agent_api_key: configMode === 'manual' ? formData.agent_api_key : undefined,
        agent_id: actualAgentId,
        is_default: formData.is_default,
        agent_instance_type: 'hive',
      };

      if (formData.channel_type === 'whatsapp') {
        createData.phone_number = formData.phone_number || null;
      } else if (formData.channel_type === 'discord') {
        if (!formData.discord_bot_token) {
          setError('Discord bot token is required for Discord instances');
          return;
        }
        createData.discord_bot_token = formData.discord_bot_token;
        createData.discord_client_id = formData.discord_client_id || null;
      }

      createMutation.mutate(createData);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const hasProviders = providers && providers.length > 0;
  const selectedProvider = providers?.find((p) => p.id === formData.agent_provider_id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{isEditing ? 'Edit Instance' : 'Connect Your Data'}</DialogTitle>
            <DialogDescription>
              {isEditing
                ? 'Update the instance configuration'
                : 'Your AI becomes truly omnichannel - present in every network.'}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Instance Name */}
            <div className="grid gap-2">
              <Label htmlFor="name">
                Instance Name *<span className="text-xs text-muted-foreground ml-2">(lowercase, no spaces)</span>
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleNameChange(e.target.value)}
                placeholder="my-whatsapp-instance"
                required
                disabled={isEditing || isPending}
              />
              {nameWarning && <p className="text-xs text-warning">{nameWarning}</p>}
            </div>

            {/* Channel Type */}
            <div className="grid gap-2">
              <Label htmlFor="channel_type">Channel Type *</Label>
              <Select
                value={formData.channel_type}
                onValueChange={(value) => setFormData({ ...formData, channel_type: value })}
                disabled={isEditing || isPending}
              >
                <SelectTrigger id="channel_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CHANNELS).map(([key, name]) => (
                    <SelectItem key={key} value={key}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* Agent Configuration Section */}
            <div className="space-y-4">
              <Label className="text-sm font-semibold">Agent Configuration</Label>

              {/* Config Mode Toggle */}
              {hasProviders && (
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant={configMode === 'provider' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleConfigModeChange('provider')}
                    disabled={isPending}
                    className="flex-1"
                  >
                    <Server className="h-4 w-4 mr-2" />
                    Provider
                  </Button>
                  <Button
                    type="button"
                    variant={configMode === 'manual' ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleConfigModeChange('manual')}
                    disabled={isPending}
                    className="flex-1"
                  >
                    <Settings2 className="h-4 w-4 mr-2" />
                    Manual
                  </Button>
                </div>
              )}

              {/* Provider Mode */}
              {configMode === 'provider' && hasProviders && (
                <>
                  {/* Provider Selection */}
                  <div className="grid gap-2">
                    <Label htmlFor="provider">Provider *</Label>
                    <Select
                      value={formData.agent_provider_id?.toString() || 'none'}
                      onValueChange={handleProviderChange}
                      disabled={isPending}
                    >
                      <SelectTrigger id="provider">
                        <SelectValue placeholder="Select provider..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">Select provider...</SelectItem>
                        {providers?.map((provider) => (
                          <SelectItem key={provider.id} value={provider.id.toString()}>
                            <span className="flex items-center gap-2">
                              {provider.name}
                              {provider.last_health_status === 'healthy' && <span className="text-green-500">●</span>}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedProvider && (
                      <p className="text-xs text-muted-foreground truncate">
                        <code>{selectedProvider.api_url}</code>
                      </p>
                    )}
                  </div>

                  {/* Agent/Team Selection */}
                  {formData.agent_provider_id && (
                    <div className="grid gap-2">
                      <Label htmlFor="agent_id">Agent / Team</Label>
                      {isLoadingItems ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Loading...
                        </div>
                      ) : agentsAndTeams.length > 0 ? (
                        <>
                          <Select
                            value={formData.agent_id || 'none'}
                            onValueChange={(value) =>
                              setFormData({ ...formData, agent_id: value === 'none' ? '' : value })
                            }
                            disabled={isPending}
                          >
                            <SelectTrigger id="agent_id">
                              <SelectValue placeholder="Select (optional)...">
                                {selectedItem && (
                                  <span className="flex items-center gap-2">
                                    {selectedItem.type === 'agent' ? (
                                      <Bot className="h-3.5 w-3.5 text-blue-500" />
                                    ) : (
                                      <Users className="h-3.5 w-3.5 text-purple-500" />
                                    )}
                                    {selectedItem.name}
                                  </span>
                                )}
                              </SelectValue>
                            </SelectTrigger>
                            <SelectContent className="max-h-60">
                              <SelectItem value="none">
                                <span className="text-muted-foreground">Default (no specific agent)</span>
                              </SelectItem>
                              {agentsAndTeams.map((item) => (
                                <SelectItem key={item.id} value={item.id}>
                                  <span className="flex items-center gap-2">
                                    {item.type === 'agent' ? (
                                      <Bot className="h-3.5 w-3.5 text-blue-500 flex-shrink-0" />
                                    ) : (
                                      <Users className="h-3.5 w-3.5 text-purple-500 flex-shrink-0" />
                                    )}
                                    <span className="truncate">{item.name}</span>
                                  </span>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {selectedItem?.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2">{selectedItem.description}</p>
                          )}
                        </>
                      ) : (
                        <Input
                          id="agent_id"
                          value={formData.agent_id}
                          onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                          placeholder="agent-uuid (optional)"
                          disabled={isPending}
                        />
                      )}
                    </div>
                  )}
                </>
              )}

              {/* Manual Mode or No Providers */}
              {(configMode === 'manual' || !hasProviders) && (
                <>
                  {!hasProviders && (
                    <Alert>
                      <AlertDescription className="text-xs">
                        💡 Create a Provider in Settings → Providers to save credentials.
                      </AlertDescription>
                    </Alert>
                  )}

                  <div className="grid gap-2">
                    <Label htmlFor="agent_api_url">Agent API URL *</Label>
                    <Input
                      id="agent_api_url"
                      type="url"
                      value={formData.agent_api_url}
                      onChange={(e) => setFormData({ ...formData, agent_api_url: e.target.value })}
                      placeholder="http://localhost:8000"
                      required={configMode === 'manual'}
                      disabled={isPending}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="agent_api_key">Agent API Key *</Label>
                    <Input
                      id="agent_api_key"
                      type="password"
                      value={formData.agent_api_key}
                      onChange={(e) => setFormData({ ...formData, agent_api_key: e.target.value })}
                      placeholder="••••••••"
                      required={configMode === 'manual'}
                      disabled={isPending}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="agent_id_manual">Agent ID</Label>
                    <Input
                      id="agent_id_manual"
                      value={formData.agent_id}
                      onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                      placeholder="agent-uuid (optional)"
                      disabled={isPending}
                    />
                  </div>
                </>
              )}
            </div>

            <Separator />

            {/* WhatsApp Fields */}
            {formData.channel_type === 'whatsapp' && (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="phone_number">Phone Number</Label>
                  <Input
                    id="phone_number"
                    value={formData.phone_number}
                    onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                    placeholder="+1234567890 (optional)"
                    disabled={isPending}
                  />
                </div>
                <Alert>
                  <AlertDescription className="text-xs">
                    ℹ️ WhatsApp config is handled automatically by the backend
                  </AlertDescription>
                </Alert>
              </>
            )}

            {/* Discord Fields */}
            {formData.channel_type === 'discord' && (
              <>
                <div className="grid gap-2">
                  <Label htmlFor="discord_bot_token">Discord Bot Token *</Label>
                  <Input
                    id="discord_bot_token"
                    type="password"
                    value={formData.discord_bot_token}
                    onChange={(e) => setFormData({ ...formData, discord_bot_token: e.target.value })}
                    placeholder="••••••••"
                    required={!isEditing}
                    disabled={isPending}
                  />
                  {isEditing && <p className="text-xs text-warning">Leave empty to keep existing</p>}
                </div>

                <div className="grid gap-2">
                  <Label htmlFor="discord_client_id">Discord Client ID</Label>
                  <Input
                    id="discord_client_id"
                    value={formData.discord_client_id}
                    onChange={(e) => setFormData({ ...formData, discord_client_id: e.target.value })}
                    placeholder="123456789012345678 (optional)"
                    disabled={isPending}
                  />
                </div>
              </>
            )}

            {/* Set as Default */}
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="h-4 w-4 rounded border-border"
                disabled={isPending}
              />
              <Label htmlFor="is_default" className="cursor-pointer text-sm">
                Set as default instance
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" className="gradient-primary" disabled={isPending}>
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {isEditing ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                <>{isEditing ? 'Update' : 'Create'}</>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
